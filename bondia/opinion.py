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


def get_day_without_opinion(days, revision, user):
    """
    Find a day the user hasn't voted on.

    Parameters
    ----------
    days : List[:class:`Day`]
        Days to choose from. Has to be sorted from older to newer days.
    revision : str
        Revision name (e.g. `rev_01`).
    user : str
        User name.

    Returns
    -------
    day : :class:`Day`
        The last (in time) day the user has not voted on yet (in the given revision). If The user already voted on all
        of them, the last day is returned.
    """
    user = user.capitalize()
    days_with_opinion = (
        DataFlagOpinion.select(DataFlagOpinion.lsd)
        .join(MediaWikiUser)
        .switch(DataFlagOpinion)
        .join(DataRevision)
        .where(MediaWikiUser.user_name == user, DataRevision.name == revision)
    )
    days_with_opinion = [d.lsd for d in days_with_opinion]
    logger.debug(
        f"Days w/ opinion for user {user}, rev {revision}: {days_with_opinion}."
    )
    for d in reversed(days):
        if d.lsd not in days_with_opinion:
            return d
    return days[-1]
