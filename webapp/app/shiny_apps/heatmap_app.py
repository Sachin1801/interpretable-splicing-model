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


def create_app(api_base_url: str = "http://localhost:8000", fastapi_app=None):
    """Create the PyShiny heatmap app.
    
    Args:
        api_base_url: Base URL for API requests (used if fastapi_app is None)
        fastapi_app: Optional FastAPI app instance for internal API calls
    """

    app_ui = ui.page_fluid(
        ui.head_content(
            ui.tags.script(f"""
                // Configuration
                var API_BASE_URL = '{api_base_url}';
                var paramsSet = false;
                var retryCount = 0;
                var maxRetries = 5;

                console.log('[Heatmap] App loaded. API_BASE_URL:', API_BASE_URL);
                console.log('[Heatmap] Current URL:', window.location.href);

                // Parse URL query parameters
                function getUrlParams() {{
                    const params = new URLSearchParams(window.location.search);
                    const result = {{
                        job_id: params.get('job_id'),
                        batch_index: params.get('batch_index')
                    }};
                    console.log('[Heatmap] URL params parsed:', result);
                    return result;
                }}

                // Set params in Shiny (from URL or postMessage)
                function setShinyParams(job_id, batch_index) {{
                    console.log('[Heatmap] setShinyParams called:', job_id, batch_index, 'paramsSet:', paramsSet);
                    if (paramsSet) {{
                        console.log('[Heatmap] Params already set, skipping');
                        return;
                    }}
                    if (typeof Shiny !== 'undefined' && Shiny.setInputValue && job_id) {{
                        console.log('[Heatmap] Setting Shiny input values:', job_id, batch_index);
                        Shiny.setInputValue('pm_job_id', job_id);
                        Shiny.setInputValue('pm_batch_index', batch_index);
                        paramsSet = true;
                    }} else {{
                        console.log('[Heatmap] Cannot set params - Shiny:', typeof Shiny, 'setInputValue:', typeof Shiny?.setInputValue, 'job_id:', job_id);
                    }}
                }}

                // Retry setting params if Shiny isn't ready
                function retrySetParams() {{
                    if (paramsSet || retryCount >= maxRetries) return;
                    retryCount++;
                    console.log('[Heatmap] Retry attempt', retryCount);
                    var urlParams = getUrlParams();
                    if (urlParams.job_id) {{
                        setShinyParams(urlParams.job_id, urlParams.batch_index);
                    }}
                    if (!paramsSet && retryCount < maxRetries) {{
                        setTimeout(retrySetParams, 500);
                    }}
                }}

                // Listen for postMessage from parent window
                window.addEventListener('message', function(event) {{
                    if (event.data && event.data.type === 'setParams') {{
                        console.log('[Heatmap] Received params via postMessage:', event.data);
                        // Wait for Shiny to be ready, then set input values
                        if (typeof Shiny !== 'undefined' && Shiny.setInputValue) {{
                            Shiny.setInputValue('pm_job_id', event.data.job_id);
                            Shiny.setInputValue('pm_batch_index', event.data.batch_index);
                        }} else {{
                           
                            // Retry after Shiny loads
                            document.addEventListener('shiny:connected', function() {{
                                Shiny.setInputValue('pm_job_id', event.data.job_id);
                                Shiny.setInputValue('pm_batch_index', event.data.batch_index);
                            }});
                        }}
                    }}
                    // Handle download request from parent
                    if (event.data && event.data.type === 'downloadRequest') {{
                        console.log('[Heatmap] Download requested');
                        var plotDiv = document.querySelector('.js-plotly-plot');
                        if (plotDiv) {{
                            Plotly.toImage(plotDiv, {{format: 'svg', width: 1200, height: 700}})
                                .then(function(dataUrl) {{
                                    window.parent.postMessage({{
                                        type: 'downloadResponse',
                                        source: 'heatmap',
                                        dataUrl: dataUrl
                                    }}, '*');
                                }})
                                .catch(function(err) {{
                                    window.parent.postMessage({{
                                        type: 'downloadResponse',
                                        source: 'heatmap',
                                        error: err.toString()
                                    }}, '*');
                                }});
                        }} else {{
                            window.parent.postMessage({{
                                type: 'downloadResponse',
                                source: 'heatmap',
                                error: 'Plot not ready'
                            }}, '*');
                        }}
                    }}
                }});

                // When Shiny connects, try URL params first, then request from parent
                document.addEventListener('shiny:connected', function() {{
                    console.log('[Heatmap] shiny:connected event fired');
                    // Try URL params immediately
                    var urlParams = getUrlParams();
                    if (urlParams.job_id) {{
                        console.log('[Heatmap] Using URL params:', urlParams);
                        setShinyParams(urlParams.job_id, urlParams.batch_index);
                    }}
                    // Also request from parent as backup
                    window.parent.postMessage({{type: 'ready', source: 'heatmap'}}, '*');
                }});

                // Also try on DOMContentLoaded as fallback
                document.addEventListener('DOMContentLoaded', function() {{
                    console.log('[Heatmap] DOMContentLoaded');
                    setTimeout(retrySetParams, 1000);
                }});
            """),
        ui.tags.style("""
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: #f9fafb;
                    margin: 0;
                    padding: 16px;
                }
                .heatmap-container {
                    background: white;
                    border-radius: 8px;
                    padding: 12px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);

                    width: 100%;
                    max-width: 1100px;
                    margin: 0 auto;
                    box-sizing: border-box;

                    overflow: hidden;         
                }
                .heatmap-container .plotly-graph-div,
                    .heatmap-container .js-plotly-plot,
                    .heatmap-container .svg-container {
                    width: 100% !important;
                    max-width: 100% !important;
                    box-sizing: border-box !important;
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
                12,
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

        print(f"[Heatmap Server] Initialized with api_base_url={api_base_url}", flush=True)

        @reactive.Effect
        @reactive.event(input.pm_job_id)
        async def on_params_received():
            """Triggered when params are received via postMessage."""

            

            job_id = input.pm_job_id()
            batch_index = input.pm_batch_index()
            print(f"[Heatmap Server] on_params_received triggered: job_id={job_id}, batch_index={batch_index}", flush=True)

            if not job_id:
                print("[Heatmap Server] job_id is empty, setting waiting message", flush=True)
                error_message.set("Waiting for job parameters...")
                return

            params_received.set(True)
            print(f"[Heatmap Server] params_received set to True", flush=True)

            try:
                # Try to use internal FastAPI app if available, otherwise use HTTP
                if fastapi_app is not None:
                    # Use TestClient for internal requests (synchronous but works)
                    from fastapi.testclient import TestClient
                    client = TestClient(fastapi_app)
                    url_path = f"/api/vis_data/{job_id}"
                    if batch_index is not None:
                        url_path += f"?batch_index={batch_index}"
                    print(f"[Heatmap Server] Making internal API request to: {url_path}", flush=True)
                    response = client.get(url_path)
                    print(f"[Heatmap Server] API response status: {response.status_code}", flush=True)
                    if response.status_code != 200:
                        raise Exception(f"API returned status {response.status_code}: {response.text}")
                    data = response.json()
                else:
                    # Fallback to HTTP request
                    url = f"{api_base_url}/api/vis_data/{job_id}"
                    if batch_index is not None:
                        url += f"?batch_index={batch_index}"
                    print(f"[Heatmap Server] Making HTTP API request to: {url}", flush=True)
                    async with httpx.AsyncClient(
                        timeout=60.0,
                        follow_redirects=True,
                        verify=False
                    ) as client:
                        response = await client.get(url)
                        print(f"[Heatmap Server] API response status: {response.status_code}", flush=True)
                        response.raise_for_status()
                        data = response.json()
                
                print(f"[Heatmap Server] API response data keys: {list(data.keys()) if data else 'None'}", flush=True)
                vis_data.set(data)
                error_message.set(None)  # Clear any error
                print("[Heatmap Server] vis_data set successfully", flush=True)
            except Exception as e:
                error_msg = f"Error fetching data: {type(e).__name__}: {str(e)}"
                print(f"[Heatmap Server] {error_msg}", flush=True)
                import traceback
                traceback.print_exc()
                error_message.set(error_msg)



        @reactive.Effect
        def trigger_initial_heatmap():
            """Force checkbox updates when data loads to trigger heatmap rendering."""
            data = vis_data.get()
            if data:
                children = data["nucleotide_activations"]["children"]
                all_filters = list_all_filters_collapsed(children)


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

            # Extract data
            full_seq = data["sequence"]
            exon = data["exon"]
            L = len(full_seq)

            

            # Build signed matrix
            M = build_signed_filter_matrix_collapsed(children, L, available_filters)

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
            filters_rev = list(reversed(available_filters))
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
                    colorbar=dict(title="Strength"),
                )
            )

            # Highlight exon region
            #fig.add_vrect(x0=start-0.5, x1=end-0.5, fillcolor="#d0d0d0", line_width=0, opacity=0.1)

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
                title="Heat Map: Filter Contributions",
                height=max(450, 18 * len(filters_rev) + 180),
               
                margin=dict(l=110, r=100, t=80, b=30),
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
            fig.update_layout(
                autosize=True,
            )
            

            # Convert to HTML with download button enabled
            html_content = fig.to_html(
                full_html=False,
                include_plotlyjs=True,
                config={
                    "responsive": True,
                    "toImageButtonOptions": {
                        "format": "svg",
                        "filename": "heatmap_view",
                        "height": 500,
                        "width": 1090,
                        "scale": 2
                    },
                    "displayModeBar": True,
                    
                    "modeBarButtons": [[
                        "zoom2d",
                        "toImage"
                    ]],
                    "displaylogo": False,
                },
            )

            return ui.HTML(html_content)

    return App(app_ui, server)


# Create the app instance
#app = create_app()
