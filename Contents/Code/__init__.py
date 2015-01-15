########################################################################################################################
#                                                                                                                      #
# This is a demo games/roms agent. Video games, emulators, roms, etc. are not a feature Plex currently offers. The     #
# only thing you will see with this is a fancy listing for your games, they won't be playable. I do not think that     #
# Plex Inc. should offer it as a feaure in the future, but authors of emulators could include support in their         #
# products so that they could download roms (and upload saved games) back to a Plex Media Server.  John O.             #
#                                                                                                                      #
########################################################################################################################

BASE_URL = 'http://thegamesdb.net/api/'

# Games
TGDB_GAME_SEARCH = '%sGetGame.php?name=%%s' % (BASE_URL)
TGDB_ID_SEARCH   = '%sGetGame.php?id=%%s' % (BASE_URL)

# We need a map of platform IDs to short names, the API has no such thing.
shortname = {"25":"3DO", "4911":"Amiga", "4914":"Amstrad", "4916":"Android", "23":"Arcade", "22":"2600", "26":"5200", "27":"7800", "28":"Jaguar", "29":"Jaguar", "4924":"Lynx", "30":"XE", "31":"Colecovision", "40":"C64", "4928":"Fairchild", "32":"Intellivision", "4915":"iOS", "37":"Mac", "4927":"Odyssey 2", "14":"Xbox", "15":"Xbox 360", "4920":"Xbox One", "4922":"NeoGeo P", "4923":"NeoGeo PC", "24":"NeoGeo", "4912":"3DS", "3":"N64", "8":"DS", "7":"NES", "4":"GB", "5":"GBA", "41":"GBC", "2":"GameCube", "4918":"Virtual Boy", "9":"Wii", "38":"Wii U", "4921":"Ouya", "1":"PC", "4917":"CD-i", "33":"Sega 32X", "21":"Sega CD", "16":"Dreamcast", "20":"Game Gear", "18":"Genesis", "35":"SMS", "36":"Mega Drive", "17":"Saturn", "4913":"ZX Spectrum", "10":"PS1", "11":"PS2", "12":"PS3", "4919":"PS4", "39":"Vita", "13":"PSP", "6":"SNES", "34":"TGFX16", "4925":"WonderSwan", "4926":"WonderSwan Color"}

########################################################################################################################

def Start():

    pass

########################################################################################################################

class TGDbAgent(Agent.Movies):

    name = 'TheGamesDB'
    languages = [
        Locale.Language.English,
    ]
    primary_provider = True

    def search(self, results, media, lang, manual): 

        platform = media.name.lower()

        # Now we have to parse (potentially) multiple results, and use *all* of those, since if someone clicks on 
        # "fix incorrect match" they should be shown alternates.
        for game in XML.ElementFromURL(url=TGDB_GAME_SEARCH % (String.Quote(media.name)), sleep=2.0).xpath('//Game'):
            score = 90

            id = game.xpath('./id/text()')[0]
            title = game.xpath('./GameTitle/text()')[0]
            title_platform = game.xpath('./Platform/text()')[0]
            platform_id = game.xpath('./PlatformId/text()')[0]

            # We'll score based on the difference between the strings.
            score = score - abs(String.LevenshteinDistance(title.lower(), media.name.lower()))

            # And also based on the differences between the plaform
            #if media.source.lower() == platform.lower():
            score += 10

            #String.Quote('Nintendo Entertainment System (NES)'))
            a = 'Nintendo Entertainment System (NES)'
            nes_to_nes_score = abs(String.LevenshteinDistance('nes', a.lower))
            genesis_score = abs(String.LevenshteinDistance('nes', 'genesis'))

            if score <= 0:
                Log.Info(" Not adding: %s; score: %d" % (title, score))
            else:
                Log(" Adding: %s; score: %d" % (title, score))
                results.Append(MetadataSearchResult(
                    id = id,
                    name = title + ' (' + shortname[platform_id] + ')',
                    score = score,
                    lang = 'en'
                ))

        # The way that TheGamesDB does search results, we can get back 40 or 50 titles. Let's get rid of all but 10.
        results.Sort('score', descending=True)
        del results[10:]

########################################################################################################################

    def update(self, metadata, media, lang, force):

        xml = XML.ElementFromURL(TGDB_ID_SEARCH % metadata.id, cacheTime=CACHE_1MONTH, sleep=2.0).xpath('//Data')[0]

        # Let's load this stuff!
        metadata.title = xml.xpath('./Game/GameTitle/text()')[0]

        try:
            summary = xml.xpath('./Game/Overview/text()')[0].replace('&amp;', '&')
            metadata.summary = String.DecodeHTMLEntities(summary)
        except:
            metadata.summary = None

        try:
            metadata.rating = float(xml.xpath('./Game/Rating/text()')[0])
        except:
            metadata.rating = None

        try:
            metadata.studio = xml.xpath('./Game/Publisher/text()')[0]
        except:
            metadata.studio = None

        try:
            # Now it's time for the collections. This should really be its own field, but we work with what we've got.
            metadata.collections.clear()
            metadata.collections.add(xml.xpath('./Game/Platform/text()')[0])
        except:
            metadata.collections.clear()

        try:
            metadata.originally_available_at = Datetime.ParseDate(xml.xpath('./Game/ReleaseDate/text()')).date()
            metadata.year = metadata.originally_available_at.year
        except:
            pass

        metadata.genres.clear()
        for genre in xml.xpath('./Game/Genres/genre/text()'):
            metadata.genres.add(genre)

        # Some prep stuff for box covers and art.
        current_posters = []
        current_art = []
        base_path = xml.xpath('./baseImgUrl/text()')[0]

        Log.Info(' Base path for posters is - ' + base_path)

        # I can't get it to sort correctly in one loop, so we're going to do two, one for front covers, one for back.
        for poster in xml.xpath("./Game/Images/boxart[@side='front']"):
            thumb_url = base_path + poster.xpath("./@thumb")[0]
            poster_url = base_path + poster.xpath("./text()")[0]

            metadata.posters[poster_url] = Proxy.Preview(HTTP.Request(thumb_url, sleep=2.0).content)
            current_posters.append(poster_url)

        for poster in xml.xpath("./Game/Images/boxart[@side='back']"):
            thumb_url = base_path + poster.xpath("./@thumb")[0]
            poster_url = base_path + poster.xpath("./text()")[0]

            metadata.posters[poster_url] = Proxy.Preview(HTTP.Request(thumb_url, sleep=2.0).content)
            current_posters.append(poster_url)

        # Remove unavailable posters.
        for key in metadata.posters.keys():
            if key not in current_posters:
                del metadata.posters[key]

        for art in xml.xpath("./Game/Images/fanart"):
            thumb_url = base_path + art.xpath("./thumb/text()")[0]
            art_url = base_path + art.xpath("./original/text()")[0]

            metadata.art[art_url] = Proxy.Preview(HTTP.Request(thumb_url, sleep=2.0).content)
            current_art.append(art_url)

        # Remove unavailable art.
        for key in metadata.art.keys():
            if key not in current_art:
                del metadata.art[key]