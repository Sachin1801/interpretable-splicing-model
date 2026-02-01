"""PyShiny app for Filter × Position heatmap visualization.

Shows collapsed filter activations with:
- Diverging colorscale (red = skipping, white = 0, blue = inclusion)
- Filter icons positioned next to y-axis labels
- Signed matrix (positive for inclusion, negative for skipping)
"""

from shiny import App, ui, render, reactive
import plotly.graph_objects as go
import httpx
import numpy as np


def list_all_filters_collapsed(children):
    """Get list of all filter names, collapsing skip_struct_* into skip_struct_ALL."""
    names = set()
    has_skip_struct = False
    for side_node in children:
        for pos_node in side_node.get("children", []):
            for feat_node in pos_node.get("children", []):
                n = feat_node["name"]
                if n.startswith("skip_struct_"):
                    has_skip_struct = True
                else:
                    names.add(n)
    out = sorted(names)
    if has_skip_struct:
        out.append("skip_struct_ALL")
    return out


def build_signed_filter_matrix_collapsed(children, L, filter_names):
    """
    Build a signed activation matrix.

    M[row, pos]:
      + strength for inclusion-side features
      - strength for skipping-side features

    Also collapses skip_struct_* into skip_struct_ALL.
    """
    name_to_row = {name: i for i, name in enumerate(filter_names)}
    M = np.zeros((len(filter_names), L), dtype=float)

    incl_node = children[0]
    skip_node = children[1]

    def add_side(side_node, sign):
        for pos_node in side_node.get("children", []):
            pos = int(pos_node["name"].split("_")[1]) - 1
            for feat_node in pos_node.get("children", []):
                fname = feat_node["name"]

                # Collapse skip_struct_* into skip_struct_ALL
                if fname.startswith("skip_struct_") and "skip_struct_ALL" in name_to_row:
                    row = name_to_row["skip_struct_ALL"]
                else:
                    if fname not in name_to_row:
                        continue
                    row = name_to_row[fname]

                s = 0.0
                for leaf in feat_node.get("children", []):
                    s += float(leaf.get("strength", 0.0))

                M[row, pos] += sign * s

    add_side(incl_node, +1.0)
    add_side(skip_node, -1.0)
    return M


def filter_to_icon_url(filter_name: str) -> str:
    """Get URL for filter icon image."""
    return f"/static/filters/{filter_name}.png"


def create_app(api_base_url: str = "http://localhost:8000"):
    """Create the PyShiny heatmap app."""

    app_ui = ui.page_fluid(
        ui.head_content(
            ui.tags.script("""
                // Parse URL query parameters as fallback
                function getUrlParams() {
                    const params = new URLSearchParams(window.location.search);
                    return {
                        job_id: params.get('job_id'),
                        batch_index: params.get('batch_index')
                    };
                }

                // Set params in Shiny (from URL or postMessage)
                function setShinyParams(job_id, batch_index) {
                    if (typeof Shiny !== 'undefined' && Shiny.setInputValue && job_id) {
                        console.log('[Heatmap] Setting params:', job_id, batch_index);
                        Shiny.setInputValue('pm_job_id', job_id);
                        Shiny.setInputValue('pm_batch_index', batch_index);
                    }
                }

                // Listen for postMessage from parent window
                window.addEventListener('message', function(event) {
                    if (event.data && event.data.type === 'setParams') {
                        console.log('[Heatmap] Received params via postMessage:', event.data);
                        setShinyParams(event.data.job_id, event.data.batch_index);
                    }
                    // Handle download request from parent
                    if (event.data && event.data.type === 'downloadRequest') {
                        console.log('[Heatmap] Download requested');
                        var plotDiv = document.querySelector('.js-plotly-plot');
                        if (plotDiv) {
                            Plotly.toImage(plotDiv, {format: 'png', width: 1200, height: 700, scale: 2})
                                .then(function(dataUrl) {
                                    window.parent.postMessage({
                                        type: 'downloadResponse',
                                        source: 'heatmap',
                                        dataUrl: dataUrl
                                    }, '*');
                                })
                                .catch(function(err) {
                                    window.parent.postMessage({
                                        type: 'downloadResponse',
                                        source: 'heatmap',
                                        error: err.toString()
                                    }, '*');
                                });
                        } else {
                            window.parent.postMessage({
                                type: 'downloadResponse',
                                source: 'heatmap',
                                error: 'Plot not ready'
                            }, '*');
                        }
                    }
                });

                // When Shiny connects, try URL params first, then request from parent
                document.addEventListener('shiny:connected', function() {
                    console.log('[Heatmap] Shiny connected');
                    // Try URL params immediately
                    var urlParams = getUrlParams();
                    if (urlParams.job_id) {
                        console.log('[Heatmap] Using URL params:', urlParams);
                        setShinyParams(urlParams.job_id, urlParams.batch_index);
                    }
                    // Also request from parent as backup
                    window.parent.postMessage({type: 'ready', source: 'heatmap'}, '*');
                });
            """),
            ui.tags.style("""
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: #f9fafb;
                    margin: 0;
                    padding: 16px;
                }
                .filter-panel {
                    background: white;
                    border-radius: 8px;
                    padding: 16px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    max-height: 600px;
                    overflow-y: auto;
                }
                .filter-section h4 {
                    margin: 0 0 8px 0;
                    font-size: 14px;
                    color: #374151;
                }
                .filter-section {
                    margin-bottom: 16px;
                }
                .heatmap-container {
                    background: white;
                    border-radius: 8px;
                    padding: 16px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }
                .error-message {
                    color: #dc2626;
                    padding: 20px;
                    text-align: center;
                }
                .loading {
                    padding: 40px;
                    text-align: center;
                    color: #6b7280;
                }
            """)
        ),
        ui.row(
            ui.column(
                3,
                ui.div(
                    {"class": "filter-panel"},
                    ui.h4("Filter × Position Heatmap"),
                    ui.p("Blue = Inclusion, Red = Skipping",
                         style="font-size: 12px; color: #6b7280; margin-bottom: 12px;"),
                    ui.div(
                        {"class": "filter-section"},
                        ui.h4("Inclusion Filters", style="color: #2563eb;"),
                        ui.output_ui("inclusion_checkboxes"),
                    ),
                    ui.div(
                        {"class": "filter-section"},
                        ui.h4("Skipping Filters", style="color: #dc2626;"),
                        ui.output_ui("skipping_checkboxes"),
                    ),
                    ui.div(
                        {"class": "filter-section"},
                        ui.h4("Structure Filters"),
                        ui.output_ui("structure_checkboxes"),
                    ),
                    ui.hr(),
                    ui.input_action_button("select_all", "Select All", class_="btn-sm"),
                    ui.input_action_button("deselect_all", "Deselect All", class_="btn-sm"),
                ),
            ),
            ui.column(
                9,
                ui.div(
                    {"class": "heatmap-container"},
                    ui.output_ui("heatmap_plot"),
                ),
            ),
        ),
    )

    def server(input, output, session):
        vis_data = reactive.Value(None)
        error_message = reactive.Value(None)
        params_received = reactive.Value(False)

        @reactive.Effect
        @reactive.event(input.pm_job_id)
        async def on_params_received():
            """Triggered when params are received via postMessage."""
            job_id = input.pm_job_id()
            batch_index = input.pm_batch_index()
            print(f"[Heatmap] Received postMessage params: job_id={job_id}, batch_index={batch_index}", flush=True)

            if not job_id:
                error_message.set("Waiting for job parameters...")
                return

            params_received.set(True)

            try:
                url = f"{api_base_url}/api/vis_data/{job_id}"
                if batch_index is not None:
                    url += f"?batch_index={batch_index}"

                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()
                    vis_data.set(data)
                    error_message.set(None)  # Clear any error
            except httpx.HTTPError as e:
                error_message.set(f"Error fetching data: {str(e)}")
            except Exception as e:
                error_message.set(f"Unexpected error: {str(e)}")

        @output
        @render.ui
        def inclusion_checkboxes():
            data = vis_data.get()
            if not data:
                return ui.p("Loading...")

            children = data["nucleotide_activations"]["children"]
            all_filters = list_all_filters_collapsed(children)
            incl_filters = [f for f in all_filters if f.startswith("incl_") and not f.startswith("incl_struct")]

            return ui.input_checkbox_group(
                "incl_filters",
                None,
                choices={f: f for f in incl_filters},
                selected=incl_filters,
            )

        @output
        @render.ui
        def skipping_checkboxes():
            data = vis_data.get()
            if not data:
                return ui.p("Loading...")

            children = data["nucleotide_activations"]["children"]
            all_filters = list_all_filters_collapsed(children)
            skip_filters = [f for f in all_filters if f.startswith("skip_") and not f.startswith("skip_struct")]

            return ui.input_checkbox_group(
                "skip_filters",
                None,
                choices={f: f for f in skip_filters},
                selected=skip_filters,
            )

        @output
        @render.ui
        def structure_checkboxes():
            data = vis_data.get()
            if not data:
                return ui.p("Loading...")

            children = data["nucleotide_activations"]["children"]
            all_filters = list_all_filters_collapsed(children)
            struct_filters = [f for f in all_filters if "struct" in f]

            return ui.input_checkbox_group(
                "struct_filters",
                None,
                choices={f: f for f in struct_filters},
                selected=struct_filters,
            )

        @reactive.Effect
        @reactive.event(input.select_all)
        def select_all_filters():
            data = vis_data.get()
            if data:
                children = data["nucleotide_activations"]["children"]
                all_filters = list_all_filters_collapsed(children)
                incl_filters = [f for f in all_filters if f.startswith("incl_") and not f.startswith("incl_struct")]
                skip_filters = [f for f in all_filters if f.startswith("skip_") and not f.startswith("skip_struct")]
                struct_filters = [f for f in all_filters if "struct" in f]
                ui.update_checkbox_group("incl_filters", selected=incl_filters)
                ui.update_checkbox_group("skip_filters", selected=skip_filters)
                ui.update_checkbox_group("struct_filters", selected=struct_filters)

        @reactive.Effect
        @reactive.event(input.deselect_all)
        def deselect_all_filters():
            ui.update_checkbox_group("incl_filters", selected=[])
            ui.update_checkbox_group("skip_filters", selected=[])
            ui.update_checkbox_group("struct_filters", selected=[])

        @reactive.Effect
        def trigger_initial_heatmap():
            """Force checkbox updates when data loads to trigger heatmap rendering."""
            data = vis_data.get()
            if data:
                children = data["nucleotide_activations"]["children"]
                all_filters = list_all_filters_collapsed(children)
                incl_filters = [f for f in all_filters if f.startswith("incl_") and not f.startswith("incl_struct")]
                skip_filters = [f for f in all_filters if f.startswith("skip_") and not f.startswith("skip_struct")]
                struct_filters = [f for f in all_filters if "struct" in f]
                ui.update_checkbox_group("incl_filters", selected=incl_filters)
                ui.update_checkbox_group("skip_filters", selected=skip_filters)
                ui.update_checkbox_group("struct_filters", selected=struct_filters)

        @output
        @render.ui
        def heatmap_plot():
            err = error_message.get()
            if err:
                return ui.div({"class": "error-message"}, err)

            data = vis_data.get()
            if not data:
                return ui.div({"class": "loading"}, "Waiting for job parameters...")

            # Get all available filters for defaults
            children = data["nucleotide_activations"]["children"]
            available_filters = list_all_filters_collapsed(children)
            default_incl = [f for f in available_filters if f.startswith("incl_") and not f.startswith("incl_struct")]
            default_skip = [f for f in available_filters if f.startswith("skip_") and not f.startswith("skip_struct")]
            default_struct = [f for f in available_filters if "struct" in f]

            # Get selected filters - default to all if inputs not yet available
            try:
                incl_selected = list(input.incl_filters()) if input.incl_filters() else default_incl
            except Exception:
                incl_selected = default_incl
            try:
                skip_selected = list(input.skip_filters()) if input.skip_filters() else default_skip
            except Exception:
                skip_selected = default_skip
            try:
                struct_selected = list(input.struct_filters()) if input.struct_filters() else default_struct
            except Exception:
                struct_selected = default_struct

            all_selected = set(incl_selected + skip_selected + struct_selected)

            if not all_selected:
                return ui.div(
                    {"class": "loading"},
                    "Select at least one filter to display the heatmap."
                )

            # Extract data
            full_seq = data["sequence"]
            exon = data["exon"]
            L = len(full_seq)

            # Filter to only selected filters
            filters = [f for f in available_filters if f in all_selected]

            # Build signed matrix
            M = build_signed_filter_matrix_collapsed(children, L, filters)

            # Get exon boundaries for highlighting
            start = full_seq.find(exon.replace("U", "T"))
            if start == -1:
                start = full_seq.upper().find(exon.upper().replace("U", "T"))
            if start == -1:
                start = 10
            end = start + len(exon)

            # Setup display
            x_pos = list(range(L))
            x_bases = list(full_seq)
            filters_rev = list(reversed(filters))
            M_rev = M[::-1, :]

            # Symmetric z range so 0 is white
            zmax = float(max(np.max(np.abs(M_rev)), 1e-6))

            # Create heatmap with diverging colorscale
            fig = go.Figure(
                data=go.Heatmap(
                    z=M_rev,
                    x=x_pos,
                    y=filters_rev,
                    zmin=-zmax,
                    zmax=zmax,
                    colorscale=[
                        (0.0, "#dc2626"),   # Red for skipping
                        (0.5, "#ffffff"),   # White for neutral
                        (1.0, "#2563eb"),   # Blue for inclusion
                    ],
                    hovertemplate="Filter %{y}<br>Base %{customdata}<br>Strength %{z:.4f}<extra></extra>",
                    customdata=np.array(x_bases)[None, :].repeat(len(filters_rev), axis=0),
                    colorbar=dict(title="Strength<br>(+ incl, - skip)"),
                )
            )

            # Highlight exon region
            fig.add_vrect(x0=start-0.5, x1=end-0.5, fillcolor="#d0d0d0", line_width=0, opacity=0.1)

            # Add filter icons to the left of y-axis labels
            fig.update_layout(images=[])
            for y in filters_rev:
                if y != "skip_struct_ALL":
                    fig.add_layout_image(
                        dict(
                            source=filter_to_icon_url(y),
                            xref="paper",
                            yref="y",
                            x=-0.03,
                            y=y,
                            xanchor="right",
                            yanchor="middle",
                            sizex=0.06,
                            sizey=0.8,
                            sizing="contain",
                            opacity=1.0,
                            layer="above",
                        )
                    )

            fig.update_layout(
                height=max(650, 18 * len(filters_rev) + 180),
                width=1050,
                margin=dict(l=130, r=20, t=80, b=30),
                xaxis=dict(
                    side="top",
                    tickmode="array",
                    tickvals=x_pos,
                    ticktext=x_bases,
                    tickfont=dict(size=9),
                    showgrid=False,
                ),
                yaxis=dict(
                    tickfont=dict(size=10),
                    categoryorder="array",
                    categoryarray=filters_rev,
                ),
            )

            # Convert to HTML with download button enabled
            html_content = fig.to_html(
                full_html=False,
                include_plotlyjs="cdn",
                config={
                    "responsive": True,
                    "toImageButtonOptions": {
                        "format": "png",
                        "filename": "heatmap_view",
                        "height": 700,
                        "width": 1200,
                        "scale": 2
                    },
                    "displayModeBar": True,
                    "modeBarButtonsToAdd": ["toImage"],
                },
            )

            return ui.HTML(html_content)

    return App(app_ui, server)


# Create the app instance
app = create_app()
