import re
import datetime
import urlparse

SF_ROOT     = 'http://www.videoportal.sf.tv'
SF_SHOWS    = SF_ROOT + '/sendungen'
SF_CHANNELS = SF_ROOT + '/channels'
SF_SEARCH   = SF_ROOT + '/suche'

ICON        = 'icon-default.png'
ART         = 'art-default.jpg'

####################################################################################################
def Start():
    Plugin.AddPrefixHandler('/video/schweizerfernsehen', GetShowOverview, 'Schweizer Fernsehen', ICON, ART)
    Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')
    MediaContainer.title1 = 'Schweizer Fernsehen'
    MediaContainer.art = R(ART)
    MediaContainer.viewGroup = 'InfoList'
    DirectoryItem.thumb = R(ICON)
    HTTP.CacheTime = CACHE_1HOUR

####################################################################################################
def UpdateCache():
    HTTP.Request(SF_SHOWS)
    HTTP.Request(SF_CHANNELS)

####################################################################################################
def GetShowOverview():
    dir = MediaContainer()
    xml = HTML.ElementFromURL(SF_SHOWS)
    for show in xml.xpath('//div[@class="az_row"]'):
        url = SF_ROOT + show.xpath('./a')[0].get('href')
        title = show.xpath('./a[@class="sendung_name"]')[0].text
        description = show.xpath('./p[@class="az_description"]')[0].text
        try:
            thumb = re.sub("width=\d+", "width=200", show.xpath('./a/img')[0].get('src'))
        except:
            thumb = None
        dir.Append(Function(DirectoryItem(GetEpisodeMenu, title=title, summary=description, thumb=Function(GetThumb, url=thumb)), url=url))
    return dir

####################################################################################################
def GetEpisodeMenu(sender, url):
    dir = MediaContainer(title2=sender.itemTitle)
    xml = HTML.ElementFromURL(url)
    try:
        show = xml.xpath('//div[@class="act_sendung_info"]')[0]
        video_url = SF_ROOT + show.xpath('./a')[0].get('href').split(';')[0]

        title = show.xpath('./div/h2/a')[0].text
        summary = ""
        for info_item in show.xpath('.//ul[@class="sendung_beitraege"]/li/a'):
            summary = summary + info_item.text + "\n"
        try:
            thumb = re.sub("width=\d+", "width=200", show.xpath('./a/img')[0].get('src'))
        except:
            thumb = None
        dir.Append(WebVideoItem(video_url, title=title, summary=summary, thumb=Function(GetThumb, url=thumb)))
    except:
        pass

    dir.Extend(GetPreviousEpisodes(sender, url, sender.itemTitle, previousEpisode=(len(dir) > 0)))

    if len(dir) == 0:
        return MessageContainer(L("No Episodes"), L("No Episodes"))
    else:
        return dir

####################################################################################################
def GetPreviousEpisodes(sender, url, showTitle, previousEpisode=False):
    dir = MediaContainer(title2=showTitle)
    xml = HTML.ElementFromURL(url)

    previous = xml.xpath('//div[@class="prev_sendungen"]')[0]
    for show in previous.xpath('.//div[@class="comment_row"]'):
        try:
            video_url = SF_ROOT + show.xpath('./div[@class="left_innner_column"]/a')[0].get('href').split(';')[0]

            title = show.xpath('./div[@class="sendung_content"]/a/strong')[0].text
            summary = ""
            for info_item in show.xpath('./div[@class="sendung_content"]/ul/li/a'):
                summary = summary + info_item.text + "\n"
            try:
                thumb = re.sub("width=\d+", "width=200", show.xpath('div/a/img[@class="thumbnail"]')[0].get('src'))
            except:
                thumb = None
            dir.Append(WebVideoItem(video_url, title=title, summary=summary, thumb=Function(GetThumb, url=thumb)))
        except:
            pass

    base_url = url.split('&page=', 1)[0]
    try:
        current_page = int(xml.xpath('//p[@class="pagination"]/a[@class="act"]')[0].text)
        max_page = 1
        try:
            for page in xml.xpath('//p[@class="pagination"]/a'):
                if (page.get('href')):
                    page_nr = int(page.get('href').rsplit('=',1)[1])
                    if (page_nr > max_page):
                        max_page = page_nr
        except:
            pass

        if (current_page < max_page):
            next_url = base_url + "&page=" + str(current_page + 1)
            dir.Append(Function(DirectoryItem(GetPreviousEpisodes, title=L("Previous Episodes"), url=next_url, thumb=R('icon-previous.png')), url=next_url, showTitle=showTitle))
            return dir
    except:
        #no additional pages
        pass

    try:
        prevURL = xml.xpath("//div[@class='grey_box sendung_nav']/a")[0].get('href')
        Log(prevURL)
        if prevURL.find("&period=") != -1:
            (url, a, date) = prevURL.rpartition("&period=")
            (year, a, month) = date.partition("-")
            year = int(year)
            month = int(month)

        prev_month = datetime.date(year=year, month=month, day=1)
        url = SF_ROOT + prevURL

        if previousEpisode or len(dir) > 0 or prev_month.year < 2000:
            dir.Append(Function(DirectoryItem(GetPreviousEpisodes, title=L("Episodes from ") + L(prev_month.strftime('%B')) + " " + str(prev_month.year), url=url, thumb=R('icon-previous.png')), url=url, showTitle=showTitle))
        else:
            dir.Extend(GetPreviousEpisodes(sender, url, showTitle))
    except:
        pass

    return dir

####################################################################################################
def GetThumb(url):
    try:
        data = HTTP.Request(url, cacheTime=CACHE_1MONTH).content
        return DataObject(data, 'image/jpeg')
    except:
        return Redirect(R(ICON))
