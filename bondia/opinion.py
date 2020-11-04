import logging

from time import time

from chimedb.dataflag import DataFlagOpinion, DataFlagOpinionType, DataRevision
from chimedb.core.mediawiki import MediaWikiUser

from . import __version__

logger = logging.getLogger(__name__)


bondia_dataflagopiniontype = {
    "name": "bondia",
    "description": "Opinion inserted by a bondia user.",
    # TODO: What do we want to put in here? The bondia version is already in DataFlagClient.
    # TODO: We could add the bondia config or the user chosen plotting parameters!?
    "metadata": {},
}


def get(lsd, revision, user):
    if lsd is None:
        return None
    user = user.capitalize()
    try:
        return (
            DataFlagOpinion.select(DataFlagOpinion.decision)
            .join(MediaWikiUser)
            .switch(DataFlagOpinion)
            .join(DataRevision)
            .where(
                MediaWikiUser.user_name == user,
                DataRevision.name == revision,
                DataFlagOpinion.lsd == lsd.lsd,
            )
            .get()
            .decision
        )
    except DataFlagOpinion.DoesNotExist:
        return None


def insert(user, lsd, revision, decision):
    if lsd is None:
        return
    user = user.capitalize()
    try:
        existing_decision = (
            DataFlagOpinion.select(DataFlagOpinion.id, DataFlagOpinion.decision)
            .join(MediaWikiUser)
            .switch(DataFlagOpinion)
            .join(DataRevision)
            .where(
                MediaWikiUser.user_name == user,
                DataRevision.name == revision,
                DataFlagOpinion.lsd == lsd.lsd,
            )
            .get()
        )
    except DataFlagOpinion.DoesNotExist:
        logger.debug(
            f"Inserting opinion of user {user} for {revision}, {lsd.lsd}: {decision}"
        )
        opinion_type, _ = DataFlagOpinionType.get_or_create(
            **bondia_dataflagopiniontype
        )
        revision, _ = DataRevision.get_or_create(name=revision)
        DataFlagOpinion.create_opinion(
            user,
            time(),
            decision,
            opinion_type.name,
            __name__,
            __version__,
            lsd.lsd,
            revision.name,
        )
    else:
        # Update the existing opinion
        logger.debug(
            f"Updating opinion of user {user} for {revision}, {lsd.lsd} (ID {existing_decision} "
            f"{existing_decision.id}): {existing_decision.decision} -> {decision}"
        )
        existing_decision.decision = decision
        existing_decision.save()


def get_days_with_opinion(revision, user):
    user = user.capitalize()
    days_with_opinion = (
        DataFlagOpinion.select(DataFlagOpinion.lsd)
        .join(MediaWikiUser)
        .switch(DataFlagOpinion)
        .join(DataRevision)
        .where(MediaWikiUser.user_name == user, DataRevision.name == revision)
    )
    return [d.lsd for d in days_with_opinion]


def get_days_without_opinion(days, revision, user):
    user = user.capitalize()
    days_with_opinion = get_days_with_opinion(revision, user)
    logger.debug(
        f"Days w/ opinion for user {user}, rev {revision}: {days_with_opinion}."
    )
    days_without_opinion = []

    for d in days:
        if d.lsd not in days_with_opinion:
            days_without_opinion.append(d)

    logger.debug(
        f"Days w/o opinion for user {user}, rev {revision}: {days_without_opinion}."
    )
    return days_without_opinion


def get_day_without_opinion(last_selected_day, days, revision, user):
    """
    Find a day the user hasn't voted on.

    Parameters
    ----------
    last_selected_day : :class:`Day` or None
        The last day that was selected.
    days : List[:class:`Day`]
        Days to choose from. Has to be sorted from older to newer days.
    revision : str
        Revision name (e.g. `rev_01`).
    user : str
        User name.

    Returns
    -------
    day : :class:`Day`
        If possible the next later day. If there is no later day without an opinion by that user, show the next older
        day without an opinion. If there is no day without opinion by that user, the last selected day is returned.
        If `last_selected_day` is None, the latest day without an opinion by that user will be returned.
    """
    user = user.capitalize()
    days_with_opinion = get_days_with_opinion(revision, user)
    logger.debug(
        f"Days w/ opinion for user {user}, rev {revision}: {days_with_opinion}."
    )

    if last_selected_day is None:
        # Simply return the latest day w/o opinion by that user
        for d in reversed(days):
            if d.lsd not in days_with_opinion:
                return d
        return days[-1]

    # index of currently selected day
    day_i = days.index(last_selected_day)

    # look for a later day w/o opinion
    for i in range(day_i, len(days)):
        if days[i].lsd not in days_with_opinion:
            return days[i]

    # look for an earlier day w/o opinion
    for i in range(day_i, 0, -1):
        if days[i].lsd not in days_with_opinion:
            return days[i]

    # keep the same day
    return last_selected_day
