# GOAL create a simple oemof-solph model which uses grid_availabilty provided either by user as timeseries or coming from main.py functions

import numpy as np
import pandas as pd
from oemof import solph
from dash import html, dcc, Dash
import plotly.graph_objects as go

try:
    from oemof_visio import ESGraphRenderer

    ES_GRAPH = True
except ModuleNotFoundError:
    ES_GRAPH = False

from main import generate_blackout_events


evaluated_days = 3
date_time_index = pd.date_range(
    start="2024-01-01", freq="H", periods=evaluated_days * 24
)

ga = pd.Series(np.random.randint(0, 2, size=(evaluated_days * 24,)))

load = pd.Series(np.random.randint(2, 30, size=(evaluated_days * 24,)))


energy_system = solph.EnergySystem(timeindex=date_time_index)


b_el = solph.Bus(label="electricity")

dso = solph.components.Source(
    label="dso",
    outputs={
        b_el: solph.Flow(
            nominal_value=solph.Investment(ep_costs=0), max=ga, variable_costs=0.1
        )
    },
)

dso_shortage = solph.components.Source(
    label="dso-dso_shortage",
    outputs={b_el: solph.Flow(variable_costs=1)},
)

demand_el = solph.components.Sink(
    label="electricity_demand",
    inputs={b_el: solph.Flow(fix=load, nominal_value=1)},
)

energy_system.add(
    b_el,
    dso,
    dso_shortage,
    demand_el,
)

# but the less accurate the results would be.
solver_option = {"gurobi": {"MipGap": "0.02"}, "cbc": {"ratioGap": "0.02"}}
solver = "cbc"

if ES_GRAPH is True:
    gr = ESGraphRenderer(energy_system, filepath="blackout_example", img_format="png")
    gr.render()

model = solph.Model(energy_system)
model.solve(
    solver=solver,
    solve_kwargs={"tee": True},
    cmdline_options=solver_option[solver],
)

results = solph.processing.convert_keys_to_strings(solph.processing.results(model))

fig_dict = gr.sankey(results)


bus_figures = []


for nd in energy_system.nodes:
    if isinstance(nd, solph.Bus):
        bus = nd.label
        fig = go.Figure(layout=dict(title=f"{bus} bus node"))
        for t, g in solph.views.node(results, node=bus)["sequences"].items():
            idx_asset = abs(t[0].index(bus) - 1)

            fig.add_trace(
                go.Scatter(
                    x=g.index, y=g.values * pow(-1, idx_asset), name=t[0][idx_asset]
                )
            )

    bus_figures.append(fig)


fig = go.Figure(data=fig_dict)

app = Dash(__name__)
app.title = "Blackouts example"
app.layout = html.Div(
    [dcc.Graph(figure=fig)]
    + [
        dcc.Graph(
            figure=fig,
        )
        for fig in bus_figures
    ]
)

app.run_server(debug=False, port=8070)
