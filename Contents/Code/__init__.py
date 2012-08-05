SF_ROOT     = 'http://www.videoportal.sf.tv'
SF_SHOWS    = SF_ROOT + '/sendungen'
SF_CHANNELS = SF_ROOT + '/channels'
SF_SEARCH   = SF_ROOT + '/suche'

TITLE       = 'Schweizer Fernsehen'
ICON        = 'icon-default.png'
ART         = 'art-default.jpg'

REGEX_IMAGE_SUB = Regex('width=\d+')

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
    for show in page.xpath('//div[@class="az_row"]'):

        url = show.xpath('./a')[0].get('href')
        if url.startswith('http://') == False:
            url = SF_ROOT + url

        title = show.xpath('./a[@class="sendung_name"]/text()')[0]
        thumb = show.xpath('.//img')[0].get('src')
        thumbs = [ REGEX_IMAGE_SUB.sub(thumb, 'width=200'), thumb ]

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

    page = HTML.ElementFromURL(url)
    show = page.xpath('//div[@class = "sendung_info"]//h1/text()')[0]

    # The most recent episode (likely to just be one)
    for episode in page.xpath('//div[@class = "act_sendung_info"]'):

        episode_url = episode.xpath('./a')[0].get('href')
        if episode_url.startswith('http://') == False:
            episode_url = SF_ROOT + episode_url

        title = ''.join(episode.xpath('.//div/h2//text()'))
        thumb = episode.xpath('.//img')[0].get('src')
        thumbs = [ REGEX_IMAGE_SUB.sub('width=200', thumb), thumb ]
        rating_string = episode.xpath('//img[@class = "stars"]')[0].get('alt')
        rating = float(rating_string.split()[0]) * 2

        description = None
        try: description = episode.xpath('.//li/a/text()')[0]
        except: pass

        oc.add(EpisodeObject(
            url = episode_url,
            show = show,
            title = title,
            summary = description,
            rating = rating,
            thumb = Resource.ContentsOfURLWithFallback(thumbs, fallback = ICON)))

    # The episodes within the last month...
    for episode in page.xpath('//div[@class = "prev_sendungen"]/div[contains(@class, "row")]'):

        episode_url = episode.xpath('.//a')[0].get('href')
        if episode_url.startswith('http://') == False:
            episode_url = SF_ROOT + episode_url

        title = ''.join(episode.xpath('.//a[@class = "sendung_title"]//text()'))
        thumb = episode.xpath('.//img')[0].get('src')
        thumbs = [ REGEX_IMAGE_SUB.sub('width=200', thumb), thumb ]
        rating_string = episode.xpath('//img[@class = "stars"]')[0].get('alt')
        rating = float(rating_string.split()[0]) * 2

        description = None
        try: description = episode.xpath('.//li/a/text()')[0]
        except: pass

        oc.add(EpisodeObject(
            url = episode_url,
            show = show,
            title = title,
            summary = description,
            rating = rating,
            thumb = Resource.ContentsOfURLWithFallback(thumbs, fallback = ICON)))

    # Add a link to the previous months content...
    try:
        previous_url = page.xpath('//div[@id = "calendar_wrapper"]//a')[0].get('href')
        if previous_url.startswith('http://') == False:
            previous_url = SF_ROOT + previous_url

        oc.add(DirectoryObject(
            key = Callback(EpisodeMenu, title = title, url = previous_url),
            title = "Voriger Monat"))

    except: pass

    if len(oc) == 0:
        return ObjectContainer(
            header = "Keine Folgen verfügbar", 
            message = "Für diese Sendung sind im Moment keine Sendungen verfügbar.")

    return oc