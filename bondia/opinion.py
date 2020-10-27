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
    try:
        return (
            DataFlagOpinion.select(DataFlagOpinion.decision)
            .join(MediaWikiUser)
            .switch(DataFlagOpinion)
            .join(DataRevision)
            .where(
                MediaWikiUser.user_name == user,
                DataRevision.name == revision,
                DataFlagOpinion.start_time == lsd.start_time,
                DataFlagOpinion.finish_time == lsd.end_time,
            )
            .get()
            .decision
        )
    except DataFlagOpinion.DoesNotExist:
        return None


def insert(user, lsd, revision, decision):
    try:
        existing_decision = (
            DataFlagOpinion.select(DataFlagOpinion.id, DataFlagOpinion.decision)
            .join(MediaWikiUser)
            .switch(DataFlagOpinion)
            .join(DataRevision)
            .where(
                MediaWikiUser.user_name == user,
                DataRevision.name == revision,
                DataFlagOpinion.start_time == lsd.start_time,
                DataFlagOpinion.finish_time == lsd.end_time,
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
            lsd.start_time,
            lsd.end_time,
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
