def generate_blackout_events(average_frequency, average_duration, daily_likelihood={}, montly_laikelyhood={}, std_frequency=0, std_duration=0):
    """
    Assumes one single grid access form one single provider

    :param average_frequency:
    :param average_duration:
    :param std_frequency:
    :param std_duration:
    :return: grid_availability --> hourly timeseries over one year with 0's for time affected by blackouts and 1 for time where grid is there
    """
    # randomly pick blackout events start based on av_frequency, daily_likelihood, and montly_likelyhood

    # randomly assign a length to each blackout event based on average_duration

    pass

def compute_blackout_kpis(grid_availability):
    """

    :param grid_availability:
    :return: total number of blackout events, total hours of blackout, 
    """
    pass