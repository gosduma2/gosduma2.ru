# coding=utf8
"""Загружаетзаконы из api.duma.gov.ru опубликованные
с последнего момента обновления и сохраняет в БД"""

import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from gosduma.models import Law
from govapi.clients import JSONClient

logger = logging.getLogger(__name__)

PUBLISHING_STAGE = 10  # from https://gist.github.com/5b513bf4d9af584a7f8d


class Command(BaseCommand):

    def save_law(self, law_data):
        event = law_data.get('lastEvent', {})
        event_stage = event.get('stage', {})
        stage_id = event_stage.get('id')
        if stage_id == PUBLISHING_STAGE:
            publishing_date = event['date']
        else:
            publishing_date = None
        defaults = dict(
            introduction_date=law_data['introductionDate'],
            publishing_date=publishing_date,
            name=law_data['name'],
            comments=law_data['comments'],
            transcript_url=law_data['transcriptUrl'],
            url=law_data['url'],
        )
        law, created = Law.objects.get_or_create(
            number=law_data['number'], defaults=defaults
        )
        # do sanity check
        if not created:
            if not law.publishing_date:
                law.publishing_date = publishing_date
                law.save()
            # FIXME comparison of unicodes, because of implicit conversion of string to date on assignment to DateField
            attributes_differ = [
                unicode(getattr(law, attr)) != unicode(defaults[attr]) for attr in defaults.keys()
            ]
            if any(attributes_differ):
                logger.error('inconsistent law %r and api %r' % (law, defaults))
        logger.debug('law %r created=%r' % (law, created))
        return law

    def handle(self, *args, **options):
        last_publishing_date = Law.objects.last_publishing_date()
        if not last_publishing_date:
            # start search from a week ago
            last_publishing_date = date.today() - timedelta(days=7)
        api_client = JSONClient(settings.GOVAPI_TOKEN, settings.GOVAPI_APP_TOKEN)
        search_options = dict(
            search_mode=2,  # only last event from help(api_client.search)
            stage=PUBLISHING_STAGE,
            event_start=last_publishing_date,
        )
        try:
            api_results = api_client.search(**search_options)
        except Exception, exc:
            logger.exception(exc)
            raise CommandError(exc)
        api_laws = api_results.get('laws', [])
        if api_laws:
            map(self.save_law, api_laws)
        else:
            logger.debug(api_results)
        # check if there're other pages to fetch
        laws_per_page = 20  # default from help(api_client.search)
        num_results = api_results.get('count', 0)
        pages_num = num_results / laws_per_page
        if num_results % laws_per_page > 0:
            pages_num += 1
        logger.info('found %d law(s) on %d page(s)' % (num_results, pages_num))
        for page in range(2, pages_num + 1):
            search_options.update({'page': page})
            try:
                api_results = api_client.search(**search_options)
            except Exception, exc:
                logger.exception(exc)
                api_results = None
                break
            else:
                map(self.save_law, api_results.get('laws', []))
