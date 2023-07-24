# PyMC Marketing

**Unlock the power of marketing analytics with PyMC-Marketing – the open source solution for smarter decision-making.** Media mix modeling and customer lifetime value modules allow businesses to make data-driven decisions about their marketing campaigns. Optimize your marketing strategy and unlock the full potential of your customer data.

## Quick links

:::::{grid} 1 1 2 2
:gutter: 2

::::{grid-item-card} Example notebooks
:class-header: sd-text-center no-border
:class-title: sd-text-center
:class-footer: no-border

{material-outlined}`menu_book;5em`
^^^^^^^^^^^^^^^

The example notebooks provide examples of using
the library in both real case scenarios
and synthetic data. They explain how to use
the library and showcase its features.

+++

:::{button-ref} notebooks/index
:expand:
:color: secondary
:click-parent:
:ref-type: doc

To the example notebooks
:::
::::
::::{grid-item-card} API Reference
:class-header: sd-text-center no-border
:class-title: sd-text-center
:class-footer: no-border

{material-outlined}`data_object;5em`
^^^^^^^^^^^^^^^

The reference guide contains a detailed description of the functions,
modules, and objects included in the library. The reference describes how the
methods work and which parameters can be used. It assumes that you have an
understanding of the key concepts.

+++

:::{button-ref} api/index
:expand:
:color: secondary
:click-parent:
:ref-type: doc

To the reference guide
:::
::::
:::::

## Installation

Install and activate an environment (e.g. `marketing_env`) with the `pymc-marketing` package from [conda-forge](https://conda-forge.org). It may look something like the following:

```bash
mamba create -c conda-forge -n marketing_env pymc-marketing
mamba activate marketing_env
```

See the official [PyMC installation guide](https://www.pymc.io/projects/docs/en/latest/installation.html) if more detail is needed.

## Quickstart

Create a new Jupyter notebook with either JupyterLab or VS Code.

### JupyterLab Notebook

After installing the `pymc-marketing` package (see above), run the following with `marketing_env` activated:

```bash
mamba install -c conda-forge jupyterlab
jupyter lab
```

### VS Code Notebook

After installing the `pymc-marketing` package (see above), run the following with `marketing_env` activated:

```bash
mamba install -c conda-forge ipykernel
```

Start VS Code and ensure that the "Jupyter" extension is installed. Press Ctrl + Shift + P and type "Python: Select Interpreter". Ensure that `marketing_env` is selected. Press Ctrl + Shift + P and type "Create: New Jupyter Notebook".

### MMM Quickstart

```python
import pandas as pd
from pymc_marketing import mmm


data_url = "https://raw.githubusercontent.com/pymc-labs/pymc-marketing/main/datasets/mmm_example.csv"
data = pd.read_csv(data_url, parse_dates=['date_week'])

model = mmm.DelayedSaturatedMMM(
    data=data,
    target_column="y",
    date_column="date_week",
    channel_columns=["x1", "x2"],
    control_columns=[
        "event_1",
        "event_2",
        "t",
        "sin_order_1",
        "cos_order_1",
        "sin_order_2",
        "cos_order_2",
    ],
    adstock_max_lag=8,
)
```

Initiate fitting and get a visualization of some of the outputs with:

```python
model.fit()
model.plot_components_contributions();
```

See the Example notebooks section for examples of further types of plot you can get, as well as introspect the results of the fitting.

### CLV Quickstart

```python
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from pymc_marketing import clv


data_url = "https://raw.githubusercontent.com/pymc-labs/pymc-marketing/main/datasets/clv_quickstart.csv"
data = pd.read_csv(data_url)

beta_geo_model = clv.BetaGeoModel(
    customer_id=data.index,
    frequency=data["frequency"],
    recency=data["recency"],
    T=data["T"],
)

beta_geo_model.fit()
```
Once fitted, we can use the model to predict the number of future purchases for known customers, the probability that they are still alive, and get various visualizations plotted. See the Examples section for more on this.

## 📞 Schedule a Consultation
Unlock your potential with a free 30-minute strategy session with our PyMC experts. Discover how open source solutions and pymc-marketing can elevate your media-mix models and customer lifetime value analyses. Boost your career and organization by making smarter, data-driven decisions. Don't wait—[claim your complimentary session](https://calendly.com/benjamin-vincent/pymc-marketing) today and lead the way in marketing and data science innovation.

## Support

This repository is supported by [PyMC Labs](https://www.pymc-labs.io).

For companies that want to use PyMC-Marketing in production, [PyMC Labs](https://www.pymc-labs.io) is available for consulting and training. We can help you build and deploy your models in production. We have experience with cutting edge Bayesian modelling techniques which we have applied to a range of business domains including marketing analytics.

:::{image} _static/labs-logo-dark.png
:align: center
:target: https://www.pymc-labs.io
:scale: 20 %
:alt: PyMC Labs logo
:class: only-dark
:::

:::{image} _static/labs-logo-light.png
:align: center
:target: https://www.pymc-labs.io
:scale: 20 %
:alt: PyMC Labs logo
:class: only-light
:::


:::{toctree}
:hidden:

guide/index
api/index
notebooks/index
:::
