# coding=utf8
"""
Модели для хранения данных, загруженных из API российской госдумы

Терминология выбрана максимально приближеной к виду возвращаемых данных.
"""
from django.db import models


class LawManager(models.Manager):

    def last_publishing_date(self):
        laws = self.all().aggregate(last_publishing_date=models.Max('publishing_date'))
        return laws['last_publishing_date']


class Law(models.Model):
    """Законопроект внесенный в госдуму

    Например результат поиска по законам https://gist.github.com/7c31fae41d86c1d3f8cd
    """
    number = models.CharField(max_length=36, db_index=True, unique=True)  # номер законопроекта
    introduction_date = models.DateField(db_index=True)  # дата внесения
    publishing_date = models.DateField(null=True, default=None, db_index=True)  # дата опубликования
    name = models.TextField()  # название
    comments = models.TextField(default='')  # комментарии
    transcript_url = models.URLField()  # адрес транскрипта обсуждения
    url = models.URLField()  # адрес законопроекта в АСОЗД (Автоматизированной Системе Обеспечения Законодательной Деятельности)

    objects = LawManager()

    def __unicode__(self):
        return self.number


class Voting(models.Model):
    """Результаты голосования депутатов по законопроекту.

    Например http://api.duma.gov.ru/api/transcript/70707-6:

        Владимир Иванович Бессонов также предлагает снять пункты 2 и 3. Ставлю на
        голосование.

                       РЕЗУЛЬТАТЫ ГОЛОСОВАНИЯ (10 час. 55 мин. 18 сек.)
        Проголосовало за               87 чел.19,3 %
        Проголосовало против            1 чел.0,2 %
        Воздержалось                    0 чел.0,0 %
        Голосовало                     88 чел.
        Не голосовало                 362 чел.80,4 %
        Результат: не принято
    """
    law = models.ForeignKey('gosduma.Law')
    order = models.PositiveIntegerField()  # порядок голосования
    title = models.TextField()  # повестка голосования
    decision = models.TextField()  # тестовый результат голосования
    pros = models.PositiveIntegerField()  # число голосов "за""
    cons = models.PositiveIntegerField()  # число голосов "против"
    abstained = models.PositiveIntegerField()  # число воздержавшихся
    voted = models.PositiveIntegerField()  # число проголосовавших
