import pandas as pd
import numpy as np


HOURS_IN_DAY = 24
DAYS_IN_YEAR = 365
MONTHS_IN_YEAR = 12


DEFAULT_DAILY_LIKELIHOOD = {
    (0, 6): 9,
    (6, 11): 10,
    (11, 14): 14,
    (14, 17): 8,
    (17, 20): 15,
    (20, 24): 9,
}


def process_daily_likelihood(blackout_probability):

    hourly_prob = {}
    for tr, w in blackout_probability.items():
        for h in range(tr[0], tr[1]):
            if 0 <= h < HOURS_IN_DAY:
                if h not in hourly_prob:
                    hourly_prob[h] = w
                else:
                    raise ValueError(
                        f"The hour {h} is used across more than one hour group, please check your input weights"
                    )
            else:
                raise ValueError(
                    f"You define hour group which go beyond the daily 24 hours: ({tr[0]},{tr[1]}) "
                )
    for h in range(0, HOURS_IN_DAY):
        if h not in hourly_prob:
            raise ValueError(
                f"The hour {h} is missing from your input blackout probability weights, please check your inputs"
            )
    return hourly_prob


def generate_blackout_events(
    average_frequency,
    average_duration,
    date_time_index=None,
    evaluated_days=None,
    daily_likelihood=None,
    montly_laikelyhood={},
    std_frequency=0.1,
    std_duration=0.1,
):
    """
    Assumes one single grid access form one single provider

    :param average_frequency:
    :param average_duration:
    :param std_frequency:
    :param std_duration:
    :return: grid_availability --> hourly timeseries over one year with 0's for time affected by blackouts and 1 for time where grid is there
    """

    timestep = 1  # hour

    if evaluated_days is None and date_time_index is not None:
        evaluated_days = (
            len(date_time_index) / HOURS_IN_DAY
        )  # assuming hourly timesteps
    elif evaluated_days is not None and date_time_index is None:
        pd.date_range(
            start="2024-01-01", freq="H", periods=evaluated_days * HOURS_IN_DAY
        )
    elif evaluated_days is None and date_time_index is None:
        raise ValueError(
            "One of 'evaluated_days' or 'date_time_index' must be provided as argument of function generate_blackout_events"
        )

    if daily_likelihood is None:
        daily_likelihood = DEFAULT_DAILY_LIKELIHOOD

    blackout_events_per_month = np.random.normal(
        loc=average_frequency,  # median value: blackout duration
        scale=average_frequency * std_frequency,  # Standard deviation
        size=MONTHS_IN_YEAR,
    )  # random values for number of blackouts
    blackout_events_per_timeframe = int(
        sum(blackout_events_per_month / DAYS_IN_YEAR * evaluated_days)
    )

    blackout_events_number = blackout_events_per_timeframe

    hourly_blackout_likelihood = process_daily_likelihood(daily_likelihood)

    # randomly pick blackout events start based on av_frequency, daily_likelihood, and montly_likelyhood

    blackout_events_time = pd.Series(0, index=date_time_index).sample(
        n=blackout_events_per_timeframe,  # number of events
        weights=pd.Series(
            date_time_index.hour.map(hourly_blackout_likelihood), index=date_time_index
        ),  # weights
        # random_state=82929,  # seed for random number generator
        replace=False,  # disallow sampling of the same row more than once.
    )

    blackout_events_time.sort_index(inplace=True)

    # randomly assign a duration to each blackout event based on average_duration
    blackout_events_duration = np.random.normal(
        loc=average_duration,  # median value: blackout duration
        scale=average_duration * std_duration,  # Standard deviation
        size=blackout_events_number,
    )

    print(
        "Accumulated blackout duration: "
        + str(round(float(sum(blackout_events_duration)), 3))
    )

    # Round so that blackout durations fit simulation timestep => here, it would make sense to simulate for small timesteps
    for item in range(0, len(blackout_events_duration)):
        blackout_events_duration[item] = (
            round(blackout_events_duration[item] / timestep) * timestep
        )

    accumulated_blackout_duration = float(sum(blackout_events_duration))
    print(
        "Accumulated blackout duration (rounded to timestep): "
        + str(round(accumulated_blackout_duration, 3))
    )

    grid_availability = pd.Series(1, index=date_time_index)
    overlapping_blackouts = 0
    blackout_count = 0
    for j, bo_start in enumerate(blackout_events_time.index[::-1]):
        # print(j, bo_start)
        bo_stop = bo_start + pd.Timedelta(
            blackout_events_duration[j] - timestep, unit="H"
        )
        bo_stop_next = bo_start + pd.Timedelta(blackout_events_duration[j], unit="H")
        # print(grid_availability.loc[bo_start:bo_stop])

        # TODO blackout happens at end of time for longer than end of time

        if (
            grid_availability.loc[bo_start:bo_stop_next].sum()
            == blackout_events_duration[j] + timestep
        ):

            blackout_count += 1
        else:
            overlapping_blackouts += 1
        grid_availability.loc[bo_start:bo_stop] = 0

    if blackout_count == 0 and overlapping_blackouts > 0:
        blackout_count = 1
    overlapping_blackouts, blackout_count

    return (
        grid_availability,
        blackout_events_duration,
        overlapping_blackouts,
        blackout_count,
    )


def compute_blackout_kpis(
    grid_availability, blackout_events_duration, overlapping_blackouts, blackout_count
):
    """

    :param grid_availability:
    :return: total number of blackout events, total hours of blackout, 
    """
    total_hours = len(grid_availability)

    accumulated_blackout_duration = blackout_events_duration.sum()
    total_grid_availability = sum(grid_availability)
    total_grid_blackout_duration = total_hours - total_grid_availability

    # Making sure that grid outage duration is equal to expected accumulated blackout duration
    if total_grid_blackout_duration != accumulated_blackout_duration:
        print(
            f"Due to {overlapping_blackouts} overlapping blackouts, the total random blackout duration ({accumulated_blackout_duration}) is not equal with the real grid unavailability ({total_grid_blackout_duration})."
        )
    # Simple estimation of reliability
    grid_reliability = 1 - total_grid_blackout_duration / total_hours

    print(
        f"Grid is not operational for {round(total_grid_blackout_duration, 2)} hours out of {total_hours}, with a reliability of {round(grid_reliability * 100, 2)} percent. \n"
    )
    grid_availability.plot()
    return grid_reliability, total_grid_blackout_duration
