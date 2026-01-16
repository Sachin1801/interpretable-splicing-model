"""PyShiny app for Filter × Position heatmap visualization."""

from shiny import App, ui, render, reactive
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import httpx
import numpy as np
from urllib.parse import parse_qs


def create_app(api_base_url: str = "http://localhost:8000"):
    """Create the PyShiny heatmap app.

    Args:
        api_base_url: Base URL for the API to fetch heatmap data
    """

    app_ui = ui.page_fluid(
        ui.head_content(
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
                    ui.h4("Filter × Position heatmap"),
                    ui.div(
                        {"class": "filter-section"},
                        ui.h4("Inclusion Filters", style="color: #22c55e;"),
                        ui.output_ui("inclusion_checkboxes"),
                    ),
                    ui.div(
                        {"class": "filter-section"},
                        ui.h4("Skipping Filters", style="color: #ef4444;"),
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
        # Reactive value to store heatmap data
        heatmap_data = reactive.Value(None)
        error_message = reactive.Value(None)
        selected_filters = reactive.Value(set())

        def get_job_id_from_url():
            """Extract job_id from URL query parameters."""
            try:
                # Access the ASGI scope to get query string
                scope = session.http_conn.scope if hasattr(session, 'http_conn') else None
                if scope and 'query_string' in scope:
                    query_string = scope['query_string'].decode('utf-8')
                    params = parse_qs(query_string)
                    if 'job_id' in params:
                        return params['job_id'][0]
            except Exception:
                pass
            return None

        @reactive.Effect
        def fetch_data():
            """Fetch heatmap data from API on app load."""
            job_id = get_job_id_from_url()

            if not job_id:
                error_message.set("No job_id provided in URL. Please access this page from a result page.")
                return

            try:
                # Fetch heatmap data from API
                with httpx.Client(timeout=30.0) as client:
                    response = client.get(f"{api_base_url}/api/heatmap/{job_id}")
                    response.raise_for_status()
                    data = response.json()
                    heatmap_data.set(data)

                    # Initialize all filters as selected
                    if data and "filter_names" in data:
                        selected_filters.set(set(data["filter_names"]))

            except httpx.HTTPError as e:
                error_message.set(f"Error fetching data: {str(e)}")
            except Exception as e:
                error_message.set(f"Unexpected error: {str(e)}")

        @output
        @render.ui
        def inclusion_checkboxes():
            data = heatmap_data.get()
            if not data or "filter_names" not in data:
                return ui.p("Loading...")

            incl_filters = [f for f in data["filter_names"] if f.startswith("incl_") and not f.startswith("incl_struct")]

            return ui.input_checkbox_group(
                "incl_filters",
                None,
                choices={f: f for f in incl_filters},
                selected=incl_filters,
            )

        @output
        @render.ui
        def skipping_checkboxes():
            data = heatmap_data.get()
            if not data or "filter_names" not in data:
                return ui.p("Loading...")

            skip_filters = [f for f in data["filter_names"] if f.startswith("skip_") and not f.startswith("skip_struct")]

            return ui.input_checkbox_group(
                "skip_filters",
                None,
                choices={f: f for f in skip_filters},
                selected=skip_filters,
            )

        @output
        @render.ui
        def structure_checkboxes():
            data = heatmap_data.get()
            if not data or "filter_names" not in data:
                return ui.p("Loading...")

            struct_filters = [f for f in data["filter_names"] if "struct" in f]

            return ui.input_checkbox_group(
                "struct_filters",
                None,
                choices={f: f for f in struct_filters},
                selected=struct_filters,
            )

        @reactive.Effect
        @reactive.event(input.select_all)
        def select_all_filters():
            data = heatmap_data.get()
            if data and "filter_names" in data:
                # Update all checkbox groups
                incl_filters = [f for f in data["filter_names"] if f.startswith("incl_") and not f.startswith("incl_struct")]
                skip_filters = [f for f in data["filter_names"] if f.startswith("skip_") and not f.startswith("skip_struct")]
                struct_filters = [f for f in data["filter_names"] if "struct" in f]

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
        def heatmap_plot():
            err = error_message.get()
            if err:
                return ui.div({"class": "error-message"}, err)

            data = heatmap_data.get()
            if not data:
                return ui.div({"class": "loading"}, "Loading heatmap data...")

            # Get selected filters from all checkbox groups
            incl_selected = list(input.incl_filters()) if input.incl_filters() else []
            skip_selected = list(input.skip_filters()) if input.skip_filters() else []
            struct_selected = list(input.struct_filters()) if input.struct_filters() else []

            all_selected = incl_selected + skip_selected + struct_selected

            if not all_selected:
                return ui.div(
                    {"class": "loading"},
                    "Select at least one filter to display the heatmap."
                )

            # Filter data based on selected filters
            filter_names = data["filter_names"]
            activations = data["activations"]
            nucleotides = data["nucleotides"]
            positions = data["positions"]

            # Get indices of selected filters
            selected_indices = [i for i, name in enumerate(filter_names) if name in all_selected]

            if not selected_indices:
                return ui.div({"class": "loading"}, "No filters selected.")

            # Create filtered activation matrix
            filtered_names = [filter_names[i] for i in selected_indices]
            filtered_activations = [activations[i] for i in selected_indices]

            # Create x-axis labels (nucleotides)
            x_labels = [f"{nucleotides[i]}" for i in range(len(nucleotides))]

            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=filtered_activations,
                x=x_labels,
                y=filtered_names,
                colorscale="Viridis",
                colorbar=dict(
                    title="Strength",
                    titleside="right",
                ),
                hovertemplate=(
                    "Position: %{x}<br>"
                    "Filter: %{y}<br>"
                    "Activation: %{z:.3f}<br>"
                    "<extra></extra>"
                ),
            ))

            fig.update_layout(
                title=dict(
                    text="Filter Activations by Position",
                    x=0.5,
                    font=dict(size=16),
                ),
                xaxis=dict(
                    title="Sequence Position",
                    tickangle=0,
                    tickfont=dict(size=8),
                    dtick=5,  # Show every 5th tick
                ),
                yaxis=dict(
                    title="Filter",
                    tickfont=dict(size=10),
                ),
                height=max(400, len(filtered_names) * 20 + 100),
                margin=dict(l=100, r=50, t=50, b=100),
            )

            # Convert to HTML
            html_content = fig.to_html(
                full_html=False,
                include_plotlyjs="cdn",
                config={"responsive": True},
            )

            return ui.HTML(html_content)

    return App(app_ui, server)


# Create the app instance
app = create_app()
