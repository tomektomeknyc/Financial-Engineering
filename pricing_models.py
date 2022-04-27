import pandas as pd
import numpy as np
import risk_kit as rk
from abc import ABC
from collections import Iterable
from scipy.optimize import broyden1


class BinomialTree(ABC):
    """
	Implements an abstract class for the mulit-period binomial pricing models.
	Uses the Lattice objects for the nodes of the tree structure.
	Parameters:
	----------
	n: int
		The number of periods for which the tree is to be made. 
		Also equivalent to the depth of the tree.
    q: float
        The probability of the security going upwards.
	"""

    @property
    def n(self):
        """
		Gets the the number of periods in the model.
		"""
        return self._n

    @n.setter
    def n(self, val):
        self._n = val

    @property
    def q(self):
        """
        Gets the probability of a security going up.
        """
        return self._q

    @q.setter
    def q(self, val):
        self._q = val

    @property
    def tree(self):
        """
		Gets the binomial tree with node as Lattice objects
        The tree for a n period model is returned in the form of a matrix as - 
        [[S0],
        [[dS0,  uS0],
        [[d2S0, duS0,   u2S0],
        .
        .
        [[dnS0, d(n-1)u1S0, ..., unS0]]                
		"""
        return self._tree

    @tree.setter
    def tree(self, tree):
        self._tree = tree

    def printtree(self):
        """
		Prints the prices of the binomial pricing tree.
		"""
        for i in range(self.n + 1):
            print("Period = " + str(i))
            print(self.tree[i][: i + 1].round(3))

    def __init__(self, n, q=0.5):
        """
		Initializes the data descriptors from the given parameters.
		"""

        self.n = n

        self.q = q

        self.tree = np.zeros([self.n + 1, self.n + 1])


class StockPricing(BinomialTree):
    """
    Implements the binomial stock pricing model. 
    Inherits the BinomialTree class.
    Parameters:
    ----------
    n: int
        Number of periods
    S0: float
        The initial price of the security
    u: float
        The upward drift of the security
    d: float
        The downward drift of the security
    c: float
        The dividend paid by the security
    """

    __doc__ += BinomialTree.__doc__

    @property
    def S0(self):
        return self._S0

    @S0.setter
    def S0(self, val):
        self._S0 = val

    @property
    def u(self):
        return self._u

    @u.setter
    def u(self, val):
        self._u = val

    @property
    def d(self):
        return self._d

    @d.setter
    def d(self, val):
        self._d = val

    @property
    def c(self):
        return self._c

    @c.setter
    def c(self, val):
        self._c = val

    def _constructTree(self):
        """
        Constructs the pricing of the binomial model for n periods.
        """
        for i in range(self.n + 1):
            for j in range(i + 1):
                price = self.S0 * (self.u ** j) * (self.d ** (i - j))
                self.tree[i, j] = price

    def __init__(self, n, S0, u, d, c=0.0):
        """
        Initializes the binomial model for the corresponding parameters.
        """

        super().__init__(n)

        self.S0 = S0

        self.u = u

        self.d = d

        self.c = c

        self._constructTree()


class FuturesPricing(BinomialTree):
    """
    Implements a futures pricing model based on the binomial model.
    Inherits the BinomialTree class.
    Parameters:
    ----------
    
    n: int
        The period of the futures contract
    model: BinomialTree
        The underlying security pricing from which the futures contract is derived.
    q: float
        The probability of an upward move.
    unpaid_coupon: float
        The amount which the underlying security earns at the end of the contract but is not 
        paid to the long position holder in the contract.
        The contract is executed immeditately after the dividend/coupon is paid.
    """

    __doc__ += BinomialTree.__doc__

    @property
    def price(self):
        return self.tree[0, 0]

    def _constructTree(self, model, coupon):
        """
        Recomputes the prices from the given model's spot prices for futures pricing.
        """

        for i in range(self.n, -1, -1):
            if i == self.n:
                self.tree[i] = model.tree[i, : (i + 1)] - coupon
            else:
                for j in range(i + 1):
                    childd = self.tree[i + 1, j]
                    childu = self.tree[i + 1, j + 1]

                    self.tree[i, j] = self.q * childu + (1 - self.q) * childd

    def __init__(self, n, model, q, unpaid_coupon=0.0):

        super().__init__(n, q)

        self._constructTree(model, unpaid_coupon)


class OptionsPricing(BinomialTree):
    """
	Implements a binomial tree based option pricing model.
    Inherits the BinomialTree class.
    Parameters
    ----------
    n: int
        Number of periods
    model: BinomialTree
        The underlying security model from which the options contract is derived.
    r: float / BinomialTree
        The rate of interest to be used. Should be a scalar if fixed and a binomial model otherwise.
    q: float
        The probability of price going up in the binomial model
    K: float
        The strike price of the option contract.
    is_call: bool
        Sets to True if the option is call and False if the option is put. Defaults to True,
    is_american: bool
        Sets to True if the option is American and False if the option is European. Defaults to False.
	"""

    __doc__ += BinomialTree.__doc__

    @property
    def K(self):
        """
        Represents the strike price of the options contract.
        """
        return self._K

    @K.setter
    def K(self, val):
        self._K = val

    @property
    def multiplier(self):
        """
        The multiplier to be used for call and put option pricing.
        Sets to 1 for call options and -1 for put options.
        """
        return self._multiplier

    @multiplier.setter
    def multiplier(self, val):
        self._multiplier = val

    @property
    def is_american(self):
        """
        Represents if the option security is american or european.
        """
        return self._is_american

    @is_american.setter
    def is_american(self, val):
        self._is_american = val

    @property
    def price(self):
        """
        Returns the current price of the option.
        """
        return self.tree[0, 0]

    @property
    def early_exercise(self):
        """
        Gets the details of early exercise of options.
        Returns a list of dictionaries sorted by time consisting of all the possible times
        when early exercise of options can be more beneficial.
        """
        result = []
        for time, no, early_ex, hold in sorted(self._early_exercise):
            data = {
                "Time": time,
                "Current Premium": early_ex,
                "Hold": hold,
            }
            result.append(data)

        return result

    def _constructTree(self, model, r):
        """
        Computes the option prices from the given pricing model and rate of interest.
        """

        if isinstance(r, int) or isinstance(r, float):
            rate = np.empty([self.n + 1, self.n + 1])
            rate.fill(r)
        else:
            rate = r.tree

        for i in range(self.n, -1, -1):
            if i == self.n:
                for j in range(i + 1):
                    self.tree[i, j] = max(
                        0, self.multiplier * (model.tree[i, j] - self.K)
                    )
            else:
                for j in range(i + 1):
                    childu = self.tree[i + 1, j + 1]
                    childd = self.tree[i + 1, j]

                    # Expected call option permium if portfolio is held
                    hold = (self.q * childu + (1 - self.q) * childd) / (1 + rate[i, j])

                    # Call option premium if portfolio is exercised
                    # Can be done only in the case of american options
                    early_ex = max(0, self.multiplier * (model.tree[i, j] - self.K))

                    if early_ex > hold:
                        self._early_exercise.append((i, j, early_ex, hold))

                    self.tree[i, j] = max(hold, early_ex) if self.is_american else hold

    def __init__(self, n, model, r, q, K, is_call=True, is_american=False):
        """
        Initializes the black scholes model and other parameters from the given parameters.
        """
        super().__init__(n, q)

        self.K = K

        self.multiplier = 1 if is_call else -1

        self.is_american = is_american

        self._early_exercise = []

        self._constructTree(model, r)


class BondPricing(BinomialTree):
    """
    Implements the binomial bond pricing model.
    Inherits the BinomialTree class.
    Parameters:
    ----------
    n: int
        The number of periods.
    F: float
        The face value of the bond.
    
    q: float
        The probability of the price going upward in the binomial model.
    u: float
        The factor by which the bond price goes up.
    d: float
        The factor by which the bond price goes down.
    c: float
        The coupon rate of the bond. Defaults to zero assuming zero coupon bond.
    hazard: dict
        If set to None, the bond is assumed to be non-defaultable. Otherwise should contain 
        a dictionary of following params:
        a: float
            The speed of hazard escalation
        b: float
            The exponential parameter of hazard
        recovery_rate: float
            The amount of interest paid back if a default occurs
        default_probability[i, j] = a * b(i - j/2) 
    """

    __doc__ += BinomialTree.__doc__

    @property
    def F(self):
        return self._F

    @F.setter
    def F(self, val):
        self._F = val

    @property
    def c(self):
        return self._c

    @c.setter
    def c(self, val):
        self._c = val

    @property
    def price(self):
        return self.tree[0, 0]

    def _compute_defaults(self, hazard):
        """
        Computes the probability of default at each node.
        h[i, j] = a * b^(i - j/2)
        Returns a tuple of hazard rates, recovery rate
        """
        h = np.zeros([self.n + 1, self.n + 1])
        r = 1

        if hazard is not None:
            a = hazard["a"]
            b = hazard["b"]
            r = hazard["recovery_rate"]
            for i in range(self.n + 1):
                for j in range(i + 1):
                    h[i, j] = a * b ** (j - i / 2)

        return (h, r)

    def _constructTree(self, r, h, recovery_rate):
        """
        Constructs the tree for bond pricing for n periods.
        """
        if isinstance(r, int) or isinstance(r, float):
            rate = np.empty([self.n + 1, self.n + 1])
            rate.fill(r)
        else:
            rate = r.tree

        coupon = self.F * self.c

        self.tree[self.n] = np.repeat(self.F + coupon, self.n + 1)
        for i in range(self.n - 1, -1, -1):
            for j in range(i + 1):
                childd = self.tree[i + 1, j]
                childu = self.tree[i + 1, j + 1]

                non_hazard_price = (
                    coupon + (self.q * childu + (1 - self.q) * childd)
                ) * (1 - h[i, j])
                hazard_price = h[i, j] * recovery_rate * self.F
                self.tree[i, j] = (non_hazard_price + hazard_price) / (1 + rate[i, j])

    def __init__(self, n, F, q, r, c=0.0, hazard=None):
        """
        Initializes the bond pricing model from the given parameters.
        """
        super().__init__(n, q)

        self.F = F

        self.c = c

        self.r = r

        h, recovery = self._compute_defaults(hazard)

        self._constructTree(r, h, recovery)


class ForwardsPricing(BinomialTree):
    """
    Implements a forwards pricing model based on the binomial model.
    Inherits the BinomialTree class.
    Parameters:
    ----------
    
    n: int
        The period of the futures contract
    model: BinomialTree
        The underlying security pricing from which the futures contract is derived.
    q: float
        The probability of an upward move.
    r: float / BinomialTree
        The rate of interest to be used. Should be a scalar if fixed and a binomial model otherwise.
    unpaid_coupon: float
        The amount which the underlying security earns at the end of the contract but is not 
        paid to the long position holder in the contract.
        The contract is executed immeditately after the dividend/coupon is paid.
    """

    __doc__ += BinomialTree.__doc__

    @property
    def r(self):
        """
        The rate of interest.
        """
        return self._r

    @r.setter
    def r(self, val):
        self._r = val

    @property
    def price(self):
        """
        Gets the price of the forward contract on the underlying security.
        """
        zcb_n = BondPricing(self.n, 1, self.q, self.r).price
        return self.tree[0, 0] / zcb_n

    def _constructTree(self, model, r, coupon):
        """
        Recomputes the prices from the given model's spot prices for futures pricing.
        """

        if isinstance(r, int) or isinstance(r, float):
            rate = np.empty([self.n + 1, self.n + 1])
            rate.fill(r)
        else:
            rate = r.tree

        for i in range(self.n, -1, -1):
            if i == self.n:
                self.tree[i] = model.tree[i, : (i + 1)] - coupon
            else:
                for j in range(i + 1):
                    childd = self.tree[i + 1, j]
                    childu = self.tree[i + 1, j + 1]

                    self.tree[i, j] = (self.q * childu + (1 - self.q) * childd) / (
                        1 + rate[i, j]
                    )

    def __init__(self, n, model, q, r, unpaid_coupon=0.0):

        super().__init__(n, q)

        self.r = r

        self._constructTree(model, r, unpaid_coupon)


class SwapsPricing(BinomialTree):
    """
    Implements a swap pricing model based on the binomial model.
    Inherits the BinomialTree class.
    
    The model assumes the last exchange is executed at n + 1 period.
    Parameters:
    ----------
    n: int
        The number of periods. Here n denotes the period at which the last payment occured.
    q: float
        The probability of the price of security going upward. 
    
    fixed_rate: float
        The fixed rate of interest to be paid/recieved in the swap contract
    start_time: int
        The period from which the exchange starts
    is_long: bool
        The type of position to be modeled, long or short.
        Long position refers to paying the fixed  interest rate 
        while short refers to paying the floating rates.
    r: BinomialTree
        The rate model for varying interest rates
    """

    __doc__ += BinomialTree.__doc__

    @property
    def fixed_rate(self):
        return self._fixed_rate

    @fixed_rate.setter
    def fixed_rate(self, val):
        self._fixed_rate = val

    @property
    def start_time(self):
        return self._start_time

    @start_time.setter
    def start_time(self, val):
        self._start_time = val

    @property
    def multiplier(self):
        return self._multiplier

    @multiplier.setter
    def multiplier(self, val):
        self._multiplier = val

    @property
    def r(self):
        return self._r

    @r.setter
    def r(self, val):
        self._r = val

    @property
    def price(self):
        return self.tree[0, 0]

    def _constructTree(self, r):
        """
        Constructs the binomial tree for pricing the swaps.
        """
        rate = r.tree

        for i in range(self.n, -1, -1):
            if i == self.n:
                self.tree[i] = (
                    (rate[i, : (i + 1)] - self.fixed_rate)
                    * self.multiplier
                    / (rate[i, : (i + 1)] + 1)
                )
            else:
                for j in range(i + 1):
                    childd = self.tree[i + 1, j]
                    childu = self.tree[i + 1, j + 1]

                    value = (self.q * childu + (1 - self.q) * childd) / (1 + rate[i, j])

                    if i >= self.start_time - 1:
                        payment = ((rate[i, j] - self.fixed_rate) * self.multiplier) / (
                            1 + rate[i, j]
                        )
                        value += payment

                    self.tree[i, j] = value

    def __init__(self, n, q, fixed_rate, start_time, is_long, r):
        """
        Initializes the model based on the given parameters.
        """

        super().__init__(n - 1, q)

        self.fixed_rate = fixed_rate

        self.start_time = start_time

        self.multiplier = 1 if is_long else -1

        self.r = r

        self._constructTree(r)


class BDTRate(BinomialTree):
    """
    Implements a black-derman-toy short rate model over the binomial tree model.
    Inherits the BinomialTree class.
    Assumes the number of periods is equal to the length of the dirft vector - 1.
    
    rate[i, j] = a[i] * exp(b[i] * j), where
    rate[i, j] - Rate of interest at period i and  state j
    a[i] - Drift at period i
    b[i] - volatility at period i
    Parameters:
    ----------
    n: int
        The number of periods.
    drift: scalar / np.array
        The list of a[i] in the black-derman-toy model
    vol: scalar / np.array
        The list of b[i] in the black-derman-toy model
    """

    __doc__ += BinomialTree.__doc__

    @property
    def a(self):
        return self._a

    @a.setter
    def a(self, val):

        if isinstance(val, int) or isinstance(val, float):
            val = np.repeat(val, self.n)
        self._a = val

    @property
    def b(self):
        return self._b

    @b.setter
    def b(self, val):

        if isinstance(val, int) or isinstance(val, float):
            val = np.repeat(val, self.n + 1)
        self._b = val

    def _constructTree(self):
        """
        Constructs the binomial tree model for interest rates based on
        the BDT equation.
        """
        for i in range(self.n + 1):
            for j in range(i + 1):
                self.tree[i, j] = self.a[i] * np.exp(self.b[j] * j)

    def __init__(self, n, drift, vol):
        """
        Initializes the model based on the given parameters.
        """

        super().__init__(n - 1)

        self.a = drift

        self.b = vol

        self._constructTree()

    @classmethod
    def calibrate(cls, n, q, vol, market_spot_rates, iterations=200):
        """
        Calibrates the optimal drift for the given market spot rates
        Initializes the model from the corresponding optimal drift and vol
        Parameters:
        ----------
        n: int
            The number of periods
        q: float
            The probability of rates going upward in the binomial model
        
        vol: scalar / np.array
            The volatility for the model
        market_spot_rates: np.array
            The current spot rates for n periods to be used for optimization
        max_iter: int
            The number of iterations for which the optimization function should run
        Returns:
        -------
        (BDTRate, error): Returns a tuple of BDTRate instance calibrated from the given parameters and
                            the squared error in the result.
        """

        def error(drift):
            rates = BDTRate(n, drift, vol)
            spot_rates = CashPricing(n, q, rates).get_spot_rates()

            error = spot_rates - market_spot_rates
            return error

        initial_guess = np.repeat(0.05, n)
        drift = broyden1(error, initial_guess, iter=iterations)
        exp_error = (error(drift) ** 2).sum()

        return cls(n, drift, vol), exp_error


class CashPricing(BinomialTree):
    """
    Implements the binomial model for pricing 1 unit of cash.
    Inherits the BinomialTree class.
    Each node of the binomial tree denotes the value of 1 unit of cash at that node.
    For example, tree[i, j] denotes the value of 1($) at period i and state j.
    Parameters:
    ----------
    n: int
        The number of periods.    
    q: float
        The probability of price going up in the binomial model
    r: BinomialTree
        The rates of interest
    """

    def _constructTree(self, r):
        """
        Constructs the binomial tree for pricing a unit of cash.
        The i, j node of the tree denotes the price of a unit of cash at period i and state j.
        """

        rate = r.tree

        self.tree[0, 0] = 1
        for i in range(1, self.n + 1):

            # The bottom most nodes
            self.tree[i, 0] = (1 - self.q) * self.tree[i - 1, 0] / (1 + rate[i - 1, 0])

            # The top most nodes
            self.tree[i, i] = (
                self.q * self.tree[i - 1, i - 1] / (1 + rate[i - 1, i - 1])
            )

            for j in range(1, i):
                par_d = self.tree[i - 1, j - 1] / (1 + rate[i - 1, j - 1])
                par_u = self.tree[i - 1, j] / (1 + rate[i - 1, j])

                self.tree[i, j] = self.q * par_d + (1 - self.q) * par_u

    def get_zcb_prices(self):
        """
        Returns the prices of zero coupon bonds for the corresponding interest rates.
        """
        return self.tree.sum(axis=1)

    def get_spot_rates(self):
        """
        Returns the spot rates for the corresponding interest rates.
        """

        zcb_prices = self.get_zcb_prices()[1:]
        spot_rates = zcb_prices ** -(1 / (np.arange(self.n) + 1)) - 1

        return spot_rates

    def __init__(self, n, q, r):

        super().__init__(n, q)

        self._constructTree(r)


class LevelPaymentMortgage(object):
    """
    Implements the class of a single fixed-rate level payment mortgage structure.
    Assumes no pre-payment. 
    Parameters:
    ----------
    P: float
        The total principal amount of the mortgage.
    r: float
        The annual rate of interest of the mortgage.
    T: int
        The total number of years for which the payment is to be made.
    """

    @property
    def P(self):
        return self._P

    @P.setter
    def P(self, val):
        self._P = val

    @property
    def r(self):
        return self._r

    @r.setter
    def r(self, val):
        self._r = val

    @property
    def T(self):
        return self._T

    @T.setter
    def T(self, val):
        self._T = val

    @property
    def periods(self):
        return self._periods

    @periods.setter
    def periods(self, val):
        self._periods = val

    @property
    def monthly_payment(self):
        """
        The monthly payment which needs to be given
        """
        c = self.r
        n = self.T * self.periods
        M0 = self.P

        payment = (M0 * c * (1 + c) ** n) / ((1 + c) ** n - 1)
        return payment

    @property
    def annualized_rate(self):
        """
        The effective annualized rate of interest after compounding periodically
        """
        return (1 + self.r) ** self.periods - 1

    def get_value(self, rate):
        """
        The effective value of the mortgage
        Parameters:
        ----------
        rate: scalar/np.array
            The risk free rate of interest to be used for discounting cash flows.
            If the rates vary over time, it should be a numpy array of expected rates
            of interest of size periods. 
        """

        B = self.monthly_payment
        n = self.T * self.periods

        if isinstance(rate, int) or isinstance(rate, float):
            rate = np.repeat(rate, n)

        t = np.arange(1, n + 1)

        value = (1 + rate) ** (-t) * B

        return value

    def __init__(self, P, r, T, periods_per_year=12):
        """
        Initializes the class instance with the given parameters.
        """

        self.P = P

        self.periods = periods_per_year

        self.r = r / periods_per_year

        self.T = T


class PassThroughMBS(object):
    """
    Implements a basic pass through mortgage backed securitization which 
    consists of only single type of mortgages and a constant prepayment factor
    in terms of the PSA.
    Parameters:
    ----------
    P: float
        The principal payment of the pool of mortgages.
    T: int
        The number of years
    loan_r: float
        The rate of interest of lending
    pass_r: float
        The rate of interest given to investors
    PSA: float
        The rate of prepayment in terms of PSA multiplier
    age: int
        The age of the pool. Defaults to 0
    periods_per_year: int
        The number of periods per year. Defualts to 12.
    """

    @property
    def P(self):
        return self._P

    @P.setter
    def P(self, val):
        self._P = val

    @property
    def T(self):
        return self._T

    @T.setter
    def T(self, val):
        self._T = val

    @property
    def loan_r(self):
        return self._loan_r

    @loan_r.setter
    def loan_r(self, val):
        self._loan_r = val

    @property
    def pass_r(self):
        return self._pass_r

    @pass_r.setter
    def pass_r(self, val):
        self._pass_r = val

    @property
    def PSA(self):
        return self._PSA

    @PSA.setter
    def PSA(self, val):
        self._PSA = val

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, val):
        self._age = val

    @property
    def periods(self):
        return self._periods

    @periods.setter
    def periods(self, val):
        self._periods = val

    @property
    def data(self):
        """
        Gets a pandas dataframe indexed by the number of periods.
        The columns contain the monthly data about the following:
        Total Payment Received:
            The payment recieved from the mortgage holders each month
        
        Principal Received:
            The principal part of the payment
        Interest Received:
            The interest part of the payment
        Total Amount Paid:
            The total amount paid back to the investors
        Principal Paid:
            The amount of principal paid back to the investors
        Interest Paid:
            The amount of interest paid back to the investors
        Earning:
            The profit earned by the firm each month
        Prepayment Rate:
            The rate of prepayment each month given by the PSA prepayment model
        Prepayment Amount:
            The amount pre-paid in each by the mortgage holder
        Total OutStanding Amount:
            The total principal amount yet to be paid
        """

        return self._data

    @data.setter
    def data(self, val):
        self._data = val

    def _compute_values(self):
        """
        Fills the data frame of computations
        """
        rem_amount = self.P
        c = self.loan_r
        d = self.pass_r
        n = self.T * self.periods
        t = self.age + 1
        mult = self.PSA / 100

        while rem_amount > 0:
            pay_rec = rem_amount * c / (1 - (1 + c) ** - (n - t + 1))
            interest_rec = rem_amount * c
            princ_rec = pay_rec - interest_rec
            interest_paid = rem_amount * d
            cpr = mult * 0.06 * (1 if t > 30 else t / 30)
            smm = 1 - (1 - cpr) ** (1 / 12)
            repay_amount = (rem_amount - princ_rec) * smm
            princ_paid = princ_rec + repay_amount
            tot_paid = princ_paid + interest_paid
            profit = pay_rec - tot_paid
            rem_amount -= princ_paid
            t += 1

            current_values = {
                "Total Payment Received": pay_rec,
                "Principal Received": princ_rec,
                "Interest Received": interest_rec,
                "Total Amount Paid": tot_paid,
                "Principal Paid": princ_paid,
                "Interest Paid": interest_paid,
                "Earning": profit,
                "Prepayment Rate": smm,
                "Prepayment Amount": repay_amount,
                "Total OutStanding Amount": rem_amount,
            }

            self.data = self.data.append(current_values, ignore_index=True)

            self.data.index += 1


    def __init__(self, P, T, loan_r, pass_r, PSA, age=0, periods_per_year=12):
        """
        Initializes the model from the given set of parameters.
        """

        self.P = P

        self.T = T

        self.loan_r = loan_r / periods_per_year

        self.pass_r = pass_r / periods_per_year

        self.PSA = PSA

        self.age = age 

        self.periods = periods_per_year

        cols = [
            "Total Payment Received",
            "Principal Received",
            "Interest Received",
            "Total Amount Paid",
            "Principal Paid",
            "Interest Paid",
            "Earning", 
            "Prepayment Rate",
            "Prepayment Amount",
            "Total OutStanding Amount",
        ]
        data = pd.DataFrame(columns=cols)
        self.data = data

        self._compute_values()