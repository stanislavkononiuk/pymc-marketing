from typing import Dict, Optional, Sequence, Union

import numpy as np
import pandas as pd
import pymc as pm
import pytensor.tensor as pt
import xarray as xr
from pymc.distributions.dist_math import check_parameters
from pymc.util import RandomState
from pytensor.tensor import TensorVariable
from scipy.special import expit, hyp2f1

from pymc_marketing.clv.models.basic import CLVModel
from pymc_marketing.clv.utils import to_xarray


class BetaGeoModel(CLVModel):
    r"""Beta-Geo Negative Binomial Distribution (BG/NBD) model

    In the BG/NBD model, the frequency of customer purchases is modelled as the time
    of each purchase has an instantaneous probability of occurrence (hazard) and, at
    every purchase, a probability of "dropout", i.e. no longer being a customer.

    Customer-specific data needed for statistical inference include 1) the total
    number of purchases (:math:`x`) and 2) the time of the last, i.e. xth, purchase. The
    omission of purchase times :math:`t_1, ..., t_x` is due to a telescoping sum in the
    exponential function of the joint likelihood; see Section 4.1 of [1] for more
    details.

    Methods below are adapted from the BetaGeoFitter class from the lifetimes package
    (see https://github.com/CamDavidsonPilon/lifetimes/).


    Parameters
    ----------
    data: pd.DataFrame
        DataFrame containing the following columns:
            * `frequency`: number of repeat purchases (with possible values 0, 1, 2, ...)
            * `recency`: time between the first and the last purchase (with possible values 0, 1, 2, ...)
            * `T`: time between the first purchase and the end of the observation period (with possible values 0, 1, 2, ...)
            * `customer_id`: unique customer identifier
    model_config: dict, optional
        Dictionary of model prior parameters. If not provided, the model will use default priors specified in the `default_model_config` class attribute.
    sampler_config: dict, optional
        Dictionary of sampler parameters. Defaults to None.

    Examples
    --------
    BG/NBD model for customer

    .. code-block:: python

        import pymc as pm
        from pymc_marketing.clv import BetaGeoModel

        model = BetaGeoFitter(
            data=pd.DataFrame({
                "frequency"=[4, 0, 6, 3, ...],
                "recency":[30.73, 1.72, 0., 0., ...]
            }),
            model_config={
                "r": pm.Gamma.dist(alpha=0.1, beta=0.1),
                "alpha": pm.Gamma.dist(alpha=0.1, beta=0.1),
                "a": pm.Gamma.dist(alpha=0.1, beta=0.1),
                "b": pm.Gamma.dist(alpha=0.1, beta=0.1),
            },
            sampler_config={
                "draws": 1000,
                "tune": 1000,
                "chains": 2,
                "cores": 2,
                "nuts_kwargs": {"target_accept": 0.95},
            },
        )
        model.build_model()
        model.fit()
        print(model.fit_summary())

        # Estimating the expected number of purchases for a randomly chosen
        # individual in a future time period of length t
        expected_num_purchases = model.expected_num_purchases(
            t=[2, 5, 7, 10],
        )

        # Predicting the customer-specific number of purchases for a future
        # time interval of length t given their previous frequency and recency
        expected_num_purchases_new_customer = model.expected_num_purchases_new_customer(
            t=[5, 5, 5, 5],
            frequency=[5, 2, 1, 8],
            recency=[7, 4, 2.5, 11],
            T=[10, 8, 10, 22],
        )

    References
    ----------
    .. [1] Fader, P. S., Hardie, B. G., & Lee, K. L. (2005). “Counting your customers”
           the easy way: An alternative to the Pareto/NBD model. Marketing science,
           24(2), 275-284. http://brucehardie.com/papers/018/fader_et_al_mksc_05.pdf
    .. [2] Fader, P. S., Hardie, B. G., & Lee, K. L. (2008). Computing
           P (alive) using the BG/NBD model. Research Note available via
           http://www.brucehardie.com/notes/021/palive_for_BGNBD.pdf.
    .. [3] Fader, P. S. & Hardie, B. G. (2013) Overcoming the BG/NBD Model’s #NUM!
           Error Problem. Research Note available via
           http://brucehardie.com/notes/027/bgnbd_num_error.pdf.
    """

    _model_type = "BG/NBD"  # Beta-Geometric Negative Binomial Distribution

    def __init__(
        self,
        data: pd.DataFrame,
        model_config: Optional[Dict] = None,
        sampler_config: Optional[Dict] = None,
    ):
        try:
            self.customer_id = data["customer_id"]
        except KeyError:
            raise KeyError("customer_id column is missing from data")
        try:
            self.frequency = data["frequency"]
        except KeyError:
            raise KeyError("frequency column is missing from data")
        try:
            self.recency = data["recency"]
        except KeyError:
            raise KeyError("recency column is missing from data")
        try:
            self.T = data["T"]
        except KeyError:
            raise KeyError("T column is missing from data")
        super().__init__(
            model_config=model_config,
            sampler_config=sampler_config,
        )
        self.data = data
        self.a_prior = self._create_distribution(self.model_config["a_prior"])
        self.b_prior = self._create_distribution(self.model_config["b_prior"])
        self.alpha_prior = self._create_distribution(self.model_config["alpha_prior"])
        self.r_prior = self._create_distribution(self.model_config["r_prior"])
        self._process_priors(self.a_prior, self.b_prior, self.alpha_prior, self.r_prior)
        # each customer's information should be encapsulated by a single data entry
        if len(np.unique(self.customer_id)) != len(self.customer_id):
            raise ValueError(
                "The BetaGeoModel expects exactly one entry per customer. More than"
                " one entry is currently provided per customer id."
            )
        self.coords = {"customer_id": self.customer_id}

    @property
    def default_model_config(self) -> Dict[str, Dict]:
        return {
            "a_prior": {"dist": "HalfFlat", "kwargs": {}},
            "b_prior": {"dist": "HalfFlat", "kwargs": {}},
            "alpha_prior": {"dist": "HalfFlat", "kwargs": {}},
            "r_prior": {"dist": "HalfFlat", "kwargs": {}},
        }

    def build_model(
        self,
    ) -> None:
        with pm.Model(coords=self.coords) as self.model:
            a = self.model.register_rv(self.a_prior, name="a")
            b = self.model.register_rv(self.b_prior, name="b")

            alpha = self.model.register_rv(self.alpha_prior, name="alpha")
            r = self.model.register_rv(self.r_prior, name="r")

            def logp(t_x, x, a, b, r, alpha, T):
                """
                The log-likelihood expression here aligns with expression (4) from [3]
                due to the possible numerical instability of expression (3).
                """
                x_non_zero = x > 0

                # Refactored for numerical error
                d1 = (
                    pt.gammaln(r + x)
                    - pt.gammaln(r)
                    + pt.gammaln(a + b)
                    + pt.gammaln(b + x)
                    - pt.gammaln(b)
                    - pt.gammaln(a + b + x)
                )

                d2 = r * pt.log(alpha) - (r + x) * pt.log(alpha + t_x)
                c3 = ((alpha + t_x) / (alpha + T)) ** (r + x)
                c4 = a / (b + x - 1)

                logp = d1 + d2 + pt.log(c3 + pt.switch(x_non_zero, c4, 0))

                return check_parameters(
                    logp,
                    a > 0,
                    b > 0,
                    alpha > 0,
                    r > 0,
                    msg="a, b, alpha, r > 0",
                )

            pm.Potential(
                "likelihood",
                logp(
                    x=self.frequency,
                    t_x=self.recency,
                    a=a,
                    b=b,
                    alpha=alpha,
                    r=r,
                    T=self.T,
                ),
            )

    def _unload_params(self):
        trace = self.idata.posterior
        a = trace["a"]
        b = trace["b"]
        alpha = trace["alpha"]
        r = trace["r"]

        return a, b, alpha, r

    # taken from https://lifetimes.readthedocs.io/en/latest/lifetimes.fitters.html
    def expected_num_purchases(
        self,
        customer_id: Union[np.ndarray, pd.Series],
        t: Union[np.ndarray, pd.Series, TensorVariable],
        frequency: Union[np.ndarray, pd.Series, TensorVariable],
        recency: Union[np.ndarray, pd.Series, TensorVariable],
        T: Union[np.ndarray, pd.Series, TensorVariable],
    ):
        r"""
        Given a purchase history/profile of :math:`x` and :math:`t_x` for an individual
        customer, this method returns the expected number of future purchases in the
        next time interval of length :math:`t`, i.e. :math:`(T, T + t]`. The closed form
        solution for this equation is available as (10) from [1] linked above. With
        :math:`\text{hyp2f1}` being the Gaussian hypergeometric function, the
        expectation is defined as below.

        .. math::

           \mathbb{E}\left[Y(t) \mid x, t_x, T, r, \alpha, a, b\right] =
           \frac
           {
            \frac{a + b + x - 1}{a - 1}\left[
                1 - \left(\frac{\alpha + T}{\alpha + T + t}\right)^{r + x}
                \text{hyp2f1}\left(
                    r + x, b + x; a + b + x, \frac{1}{\alpha + T + t}
                \right)
            \right]
           }
           {
            1 + \delta_{x > 0} \frac{a}{b + x - 1} \left(
                \frac{\alpha + T}{\alpha + T + t}
            \right)^{r + x}
           }
        """
        t = np.asarray(t)
        if t.size != 1:
            t = to_xarray(customer_id, t)

        T = np.asarray(T)
        if T.size != 1:
            T = to_xarray(customer_id, T)

        # print(customer_id)
        frequency, recency = to_xarray(customer_id, frequency, recency)

        a, b, alpha, r = self._unload_params()

        numerator = 1 - ((alpha + T) / (alpha + T + t)) ** (r + frequency) * hyp2f1(
            r + frequency,
            b + frequency,
            a + b + frequency - 1,
            t / (alpha + T + t),
        )
        numerator *= (a + b + frequency - 1) / (a - 1)
        denominator = 1 + (frequency > 0) * (a / (b + frequency - 1)) * (
            (alpha + T) / (alpha + recency)
        ) ** (r + frequency)

        return (numerator / denominator).transpose(
            "chain", "draw", "customer_id", missing_dims="ignore"
        )

    def expected_probability_alive(
        self,
        customer_id: Union[np.ndarray, pd.Series],
        frequency: Union[np.ndarray, pd.Series],
        recency: Union[np.ndarray, pd.Series],
        T: Union[np.ndarray, pd.Series],
    ):
        r"""
        Posterior expected value of the probability of being alive at time T. The
        derivation of the closed form solution is available in [2].

        .. math::
            P\left\text{alive} \mid x, t_x, T, r, \alpha, a, b\right)
            = 1 \Big/
                \left\{
                    1 + \delta_{x>0} \frac{a}{b + x - 1}
                        \left(
                            \frac{\alpha + T}{\alpha + t_x}^{r + x}
                        \right)^{r x}
                \right\}
        """
        T = np.asarray(T)
        if T.size != 1:
            T = to_xarray(customer_id, T)

        frequency, recency = to_xarray(customer_id, frequency, recency)

        a, b, alpha, r = self._unload_params()

        log_div = (r + frequency) * np.log((alpha + T) / (alpha + recency)) + np.log(
            a / (b + np.maximum(frequency, 1) - 1)
        )

        return xr.where(frequency == 0, 1.0, expit(-log_div)).transpose(
            "chain", "draw", "customer_id", missing_dims="ignore"
        )

    def expected_num_purchases_new_customer(
        self,
        t: Union[np.ndarray, pd.Series],
    ):
        r"""
        Posterior expected number of purchases for any interval of length :math:`t`. See
        equation (9) of [1].

        The customer_id shouldn't matter too much here since no individual-specific data
        is conditioned on.

        .. math::
            \mathbb{E}\left(X(t) \mid r, \alpha, a, b \right)
            = \frac{a + b - 1}{a - 1}
            \left[
                1 - \left(\frac{\alpha}{\alpha + t}\right)^r
                \text{hyp2f1}\left(r, b; a + b - 1; \frac{t}{\alpha + t}\right)
            \right]

        """
        t = np.asarray(t)
        if t.size != 1:
            t = to_xarray(range(len(t)), t, dim="t")

        a, b, alpha, r = self._unload_params()

        left_term = (a + b - 1) / (a - 1)
        right_term = 1 - (alpha / (alpha + t)) ** r * hyp2f1(
            r, b, a + b - 1, t / (alpha + t)
        )

        return (left_term * right_term).transpose(
            "chain", "draw", "t", missing_dims="ignore"
        )

    def _distribution_new_customers(
        self,
        random_seed: Optional[RandomState] = None,
        var_names: Sequence[str] = ("population_dropout", "population_purchase_rate"),
    ) -> xr.Dataset:
        with pm.Model():
            a = pm.HalfFlat("a")
            b = pm.HalfFlat("b")
            alpha = pm.HalfFlat("alpha")
            r = pm.HalfFlat("r")

            # This is the shape with fit_method="map"
            if self.fit_result.dims == {"chain": 1, "draw": 1}:
                shape_kwargs = {"shape": 1000}
            else:
                shape_kwargs = {}

            pm.Beta("population_dropout", alpha=a, beta=b, **shape_kwargs)
            pm.Gamma("population_purchase_rate", alpha=r, beta=alpha, **shape_kwargs)

            return pm.sample_posterior_predictive(
                self.fit_result,
                var_names=var_names,
                random_seed=random_seed,
            ).posterior_predictive

    def distribution_new_customer_dropout(
        self,
        random_seed: Optional[RandomState] = None,
    ) -> xr.Dataset:
        """Sample the Beta distribution for the population-level dropout rate.

        This is the probability that a new customer will not make another purchase ("drops out")
        immediately after any previous purchase.

        Parameters
        ----------
        random_seed : RandomState, optional
            Random state to use for sampling.

        Returns
        -------
        xr.Dataset
            Dataset containing the posterior samples for the population-level dropout rate.
        """
        return self._distribution_new_customers(
            random_seed=random_seed,
            var_names=["population_dropout"],
        )["population_dropout"]

    def distribution_new_customer_purchase_rate(
        self,
        random_seed: Optional[RandomState] = None,
    ) -> xr.Dataset:
        """Sample the Gamma distribution for the population-level purchase rate.

        This is the purchase rate for a new customer and determines the time between
        purchases for any new customer.

        Parameters
        ----------
        random_seed : RandomState, optional
            Random state to use for sampling.

        Returns
        -------
        xr.Dataset
            Dataset containing the posterior samples for the population-level purchase rate.
        """
        return self._distribution_new_customers(
            random_seed=random_seed,
            var_names=["population_purchase_rate"],
        )["population_purchase_rate"]
