# -*- coding: utf-8 -*-

SF_ROOT     = 'http://www.srf.ch'
SF_SHOWS    = SF_ROOT + '/player/tv/sendungen'
SF_CHANNELS = SF_ROOT + '/player/tv/channels'
SF_SEARCH   = SF_ROOT + '/player/tv/suche'

TITLE       = 'Schweizer Fernsehen'
ICON        = 'icon-default.png'
ART         = 'art-default.jpg'

REGEX_IMAGE_SUB = Regex('width=\d+')
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]

####################################################################################################
def Start():
    Plugin.AddPrefixHandler('/video/schweizerfernsehen', MainMenu, TITLE, ICON, ART)
    Plugin.AddViewGroup('InfoList', viewMode = 'InfoList', mediaType = 'items')

    ObjectContainer.title1 = TITLE
    ObjectContainer.art = R(ART)
    ObjectContainer.view_group = 'InfoList'

    DirectoryObject.art = R(ART)
    DirectoryObject.thumb = R(ICON)
    EpisodeObject.art = R(ART)
    EpisodeObject.thumb = R(ICON)

    HTTP.CacheTime = CACHE_1HOUR

####################################################################################################
def MainMenu():
    oc = ObjectContainer()

    page = HTML.ElementFromURL(SF_SHOWS)

    for show in page.xpath('//li[contains(@class, "az_item")]'):
        url = show.xpath('./a')[0].get('href')
        if url.startswith('http://') == False:
            url = SF_ROOT + url

        title = show.xpath('.//a[@class="sendung_name"]/text()')[0]
        thumb = show.xpath('.//img')[0].get('src')
        thumbs = [ REGEX_IMAGE_SUB.sub(thumb, 'width=500'), thumb ]

        description = None
        try: description = show.xpath('./p[@class="az_description"]/text()')[0]
        except: pass

        oc.add(DirectoryObject(
            key = Callback(EpisodeMenu, title = title, url = url),
            title = title,
            summary = description,
            thumb = Resource.ContentsOfURLWithFallback(thumbs, fallback = ICON)))

    return oc

####################################################################################################
def EpisodeMenu(title, url):
    oc = ObjectContainer(title2 = title)

    try:
        for ep in readEpisodes(url):
            oc.add(ep)
    except IndexError:
        pass

    if len(oc) == 0 and 'period=' not in url:
        return ObjectContainer(
            header = unicode(Locale.LocalString("No Episodes")),
            message =  unicode(Locale.LocalString("This show has no episodes available.")))

    # Add a link to the previous months content...
    page = HTML.ElementFromURL(url)
    try:
        if 'period=' in url:
            year_month = url.split('period=')[1]
            (year, month) = map(lambda x: int(x), year_month.split('-'))
        else:
            month_year = ''.join(page.xpath('//div[@id = "act_month_year"]/text()'))
            (month, year) = month_year.split(' ')
            now = Datetime.Now()
            year = int(year)
            month = MONTHS.index(month) + 1

        if month == 1:
            month = 12
            year = year - 1
        else:
            month = month - 1

        if 'period=' in url:
            previous_url = Regex('period=\d+-\d+').sub('period=%d-%d' % (year, month), url)
        else:
            previous_url = url + "&period=%d-%d" % (year, month)

        oc.add(DirectoryObject(
            key = Callback(EpisodeMenu, title = title, url = previous_url),
            title =  Locale.LocalString("Previous Month")))

    except: pass

    return oc

def readEpisodes(url):
    episodes = []
    page = HTML.ElementFromURL(url)
    show = page.xpath('//div[@id = "sendung_info"]/h1[@id = "title"]/text()')[0]

    # The most recent episode (likely to just be one)
    for episode in page.xpath('//li[@class = "sendung_item"]'):
        episode_url = episode.xpath('.//a')[0].get('href')
        if episode_url.startswith('http://') == False:
            episode_url = SF_ROOT + episode_url

        title = ''.join(episode.xpath('.//h2[@class="title"]/a/text()'))
        try:
            title += ' ' + ''.join(episode.xpath('.//div[@class="title_date"]/text()'))
        except:
            pass
        thumb = episode.xpath('.//img')[0].get('src')
        thumbs = [ REGEX_IMAGE_SUB.sub('width=500', thumb), thumb ]

        description = ''.join(episode.xpath('.//div[@class="description"]/text()'))

        episodes.append(EpisodeObject(
            url = episode_url,
            show = show,
            title = title,
            summary = description,
            thumb = Resource.ContentsOfURLWithFallback(thumbs, fallback = ICON)))

    # get paged content for current month
    try:
        url = page.xpath('.//a[contains(@class, "next_page")]')[0].get('href')
        return episodes + readEpisodes(SF_ROOT + url)
    except:
        pass

    return episodes
