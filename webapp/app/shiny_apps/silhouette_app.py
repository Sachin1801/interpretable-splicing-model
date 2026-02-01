"""PyShiny app for Silhouette View visualization.

Shows per-position inclusion/skipping strengths as a bar chart.
Blue bars (upward) = Inclusion strength
Red bars (downward) = Skipping strength
"""

import matplotlib
matplotlib.use('Agg')  # Must be before pyplot import for headless environments
import matplotlib.pyplot as plt
from shiny import App, ui, render, reactive
import numpy as np
import httpx


def parse_total_position_strengths(nucleotide_activations_children, L):
    """
    Parse total position strengths from nucleotide activations.

    Args:
        nucleotide_activations_children: result["nucleotide_activations"]["children"]
        L: sequence length

    Returns:
        (incl_total, skip_total) arrays of shape (L,)
    """
    def side_to_total(side_node):
        total = np.zeros(L, dtype=float)
        for pos_node in side_node.get("children", []):
            pos = int(pos_node["name"].split("_")[1]) - 1
            s = 0.0
            for feat_node in pos_node.get("children", []):
                for leaf in feat_node.get("children", []):
                    s += float(leaf.get("strength", 0.0))
            total[pos] = s
        return total

    incl_node = nucleotide_activations_children[0]
    skip_node = nucleotide_activations_children[1]
    return side_to_total(incl_node), side_to_total(skip_node)


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


def position_totals_for_selected_filters(nucleotide_activations_children, L, selected):
    """Calculate position totals for only selected filters."""
    selected = set(selected)
    expand_skip_struct = "skip_struct_ALL" in selected

    def side_to_total(side_node):
        total = np.zeros(L, dtype=float)
        for pos_node in side_node.get("children", []):
            pos = int(pos_node["name"].split("_")[1]) - 1
            s = 0.0
            for feat_node in pos_node.get("children", []):
                name = feat_node["name"]
                is_skip_struct = name.startswith("skip_struct_")
                take = (name in selected) or (expand_skip_struct and is_skip_struct)
                if not take:
                    continue
                for leaf in feat_node.get("children", []):
                    s += float(leaf.get("strength", 0.0))
            total[pos] = s
        return total

    incl_node = nucleotide_activations_children[0]
    skip_node = nucleotide_activations_children[1]
    return side_to_total(incl_node), side_to_total(skip_node)


def create_app(api_base_url: str = "http://localhost:8000"):
    """Create the PyShiny silhouette app."""

    app_ui = ui.page_fluid(
        ui.head_content(
            ui.tags.script("""
                // Listen for postMessage from parent window
                window.addEventListener('message', function(event) {
                    if (event.data && event.data.type === 'setParams') {
                        console.log('[Silhouette] Received params via postMessage:', event.data);
                        // Wait for Shiny to be ready, then set input values
                        if (typeof Shiny !== 'undefined' && Shiny.setInputValue) {
                            Shiny.setInputValue('pm_job_id', event.data.job_id);
                            Shiny.setInputValue('pm_batch_index', event.data.batch_index);
                        } else {
                            // Retry after Shiny loads
                            document.addEventListener('shiny:connected', function() {
                                Shiny.setInputValue('pm_job_id', event.data.job_id);
                                Shiny.setInputValue('pm_batch_index', event.data.batch_index);
                            });
                        }
                    }
                    // Handle download request from parent
                    if (event.data && event.data.type === 'downloadRequest') {
                        console.log('[Silhouette] Download requested');
                        var img = document.querySelector('.plot-container img');
                        if (img && img.src) {
                            window.parent.postMessage({
                                type: 'downloadResponse',
                                source: 'silhouette',
                                dataUrl: img.src
                            }, '*');
                        } else {
                            window.parent.postMessage({
                                type: 'downloadResponse',
                                source: 'silhouette',
                                error: 'Image not ready'
                            }, '*');
                        }
                    }
                });
                // Request params from parent when Shiny is ready
                document.addEventListener('shiny:connected', function() {
                    console.log('[Silhouette] Shiny connected, requesting params from parent');
                    window.parent.postMessage({type: 'ready', source: 'silhouette'}, '*');
                });
            """),
            ui.tags.style("""
                html, body {
                    height: 100%;
                    margin: 0;
                }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: #f9fafb;
                    padding: 16px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-sizing: border-box;
                }
                .container-fluid {
                    width: 100%;
                }
                .filter-panel {
                    background: white;
                    border-radius: 8px;
                    padding: 16px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    max-height: 413px;
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
                .plot-container {
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
                    ui.h4("Filter Selection"),
                    ui.p("Select which filters contribute to the silhouette view:",
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
                    {"class": "plot-container"},
                    ui.output_ui("silhouette_plot"),
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
            print(f"[Silhouette] Received postMessage params: job_id={job_id}, batch_index={batch_index}", flush=True)

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

        @output
        @render.ui
        def silhouette_plot():
            err = error_message.get()
            if err:
                return ui.div({"class": "error-message"}, err)

            data = vis_data.get()
            if not data:
                return ui.div({"class": "loading"}, "Waiting for job parameters...")

            # Get selected filters
            incl_selected = list(input.incl_filters()) if input.incl_filters() else []
            skip_selected = list(input.skip_filters()) if input.skip_filters() else []
            struct_selected = list(input.struct_filters()) if input.struct_filters() else []
            all_selected = incl_selected + skip_selected + struct_selected

            if not all_selected:
                return ui.div(
                    {"class": "loading"},
                    "Select at least one filter to display the silhouette view."
                )

            # Extract data
            full_seq = data["sequence"]
            exon = data["exon"]
            struct_full = data["structs"]
            L = len(full_seq)
            children = data["nucleotide_activations"]["children"]

            # Calculate full range from all filters for fixed y-axis
            incl_total_all, skip_total_all = parse_total_position_strengths(children, L)
            start = full_seq.find(exon.replace("U", "T"))
            if start == -1:
                start = full_seq.upper().find(exon.upper().replace("U", "T"))
            if start == -1:
                start = 10  # Default flanking length
            end = start + len(exon)

            # Get full range for y-axis
            incl_exon_all = incl_total_all[start:end]
            skip_exon_all = skip_total_all[start:end]
            y_max_all = max(
                np.max(incl_exon_all) if len(incl_exon_all) > 0 else 0,
                np.max(skip_exon_all) if len(skip_exon_all) > 0 else 0
            )
            y_max_all = max(y_max_all, 0.1)
            y_min_all = -y_max_all

            # Calculate values for selected filters
            incl_total, skip_total = position_totals_for_selected_filters(children, L, all_selected)

            # Create plot
            x = np.arange(L)
            bases = list(full_seq)

            fig, ax = plt.subplots(figsize=(21, 6))

            ax.bar(x, incl_total, width=1, color="#bed2fd", label="Inclusion")
            ax.bar(x, -skip_total, width=1, color="#f0a5a5", label="Skipping")

            # Shade exon region
            ax.axvspan(start - 0.5, end - 0.5, color="#d0d0d0", alpha=0.15)
            ax.axhline(0, linewidth=1, color='black')

            ax.set_xticks(x)
            ax.set_xticklabels(bases, fontsize=7)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            # Add secondary structure on second x-axis
            ax2 = ax.twiny()
            ax2.set_xlim(ax.get_xlim())
            ax2.xaxis.set_ticks_position("bottom")
            ax2.xaxis.set_label_position("bottom")
            ax2.spines["bottom"].set_position(("outward", 18))
            ax2.spines["top"].set_visible(False)
            ax2.spines["bottom"].set_visible(False)
            ax2.set_xticks(x)
            ax2.set_xticklabels(list(struct_full), fontsize=7)
            ax2.tick_params(axis="x", length=0, pad=2)

            # Fixed symmetric limits
            ax.set_ylim(y_min_all, y_max_all)

            # Integer tick marks
            max_tick = int(np.ceil(max(abs(y_min_all), abs(y_max_all))))
            ticks = np.arange(-max_tick, max_tick + 1, 1)
            ax.set_yticks(ticks)
            ax.set_yticklabels([str(abs(t)) for t in ticks])

            ax.set_title("Silhouette View - Position-wise Filter Contributions")
            ax.set_ylabel("Strength (a.u.)")
            ax.legend(loc='upper right', frameon=False)

            plt.tight_layout()

            # Convert to PNG
            import io
            import base64
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)

            return ui.HTML(f'<img src="data:image/png;base64,{img_base64}" style="max-width: 100%; height: auto;" />')

    return App(app_ui, server)


# Create the app instance
app = create_app()
