#!/usr/bin/env python3
from requests import post as rpost
from markdown import markdown
from random import choice
from datetime import datetime
from calendar import month_name
from pycountry import countries as conn
from urllib.parse import quote as q

from bot import bot, LOGGER, config_dict, user_data
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import get_readable_time
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex


ANIME_GRAPHQL_QUERY = """
query ($id: Int, $idMal: Int, $search: String) {
  Media(id: $id, idMal: $idMal, type: ANIME, search: $search) {
    id
    idMal
    title {
      romaji
      english
      native
    }
    type
    format
    status(version: 2)
    description(asHtml: false)
    startDate {
      year
      month
      day
    }
    endDate {
      year
      month
      day
    }
    season
    seasonYear
    episodes
    duration
    chapters
    volumes
    countryOfOrigin
    source
    hashtag
    trailer {
      id
      site
      thumbnail
    }
    updatedAt
    coverImage {
      large
    }
    bannerImage
    genres
    synonyms
    averageScore
    meanScore
    popularity
    trending
    favourites
    tags {
      name
      description
      rank
    }
    relations {
      edges {
        node {
          id
          title {
            romaji
            english
            native
          }
          format
          status
          source
          averageScore
          siteUrl
        }
        relationType
      }
    }
    characters {
      edges {
        role
        node {
          name {
            full
            native
          }
          siteUrl
        }
      }
    }
    studios {
      nodes {
         name
         siteUrl
      }
    }
    isAdult
    nextAiringEpisode {
      airingAt
      timeUntilAiring
      episode
    }
    airingSchedule {
      edges {
        node {
          airingAt
          timeUntilAiring
          episode
        }
      }
    }
    externalLinks {
      url
      site
    }
    rankings {
      rank
      year
      context
    }
    reviews {
      nodes {
        summary
        rating
        score
        siteUrl
        user {
          name
        }
      }
    }
    siteUrl
  }
}
"""

character_query = """
query ($id: Int, $search: String) {
    Character (id: $id, search: $search) {
        id
        name {
            first
            last
            full
            native
        }
        siteUrl
        image {
            large
        }
        description
    }
}
"""

manga_query = """
query ($id: Int,$search: String) { 
    Media (id: $id, type: MANGA,search: $search) { 
        id
        title {
            romaji
            english
            native
        }
        description (asHtml: false)
        startDate{
            year
        }
        type
        format
        status
        siteUrl
        averageScore
        genres
        bannerImage
    }
}
"""

url = "https://graphql.anilist.co"
sptext = ""


async def anilist(_, msg, aniid=None, u_id=None):
    if not aniid:
        user_id = msg.from_user.id
        squery = (msg.text).split(" ", 1)
        if len(squery) == 1:
            await sendMessage(
                msg, "<i>Provide AniList ID / Anime Name / MyAnimeList ID</i>"
            )
            return
        vars = {"search": squery[1]}
    else:
        user_id = int(u_id)
        vars = {"id": aniid}
    if (
        animeResp := rpost(url, json={"query": ANIME_GRAPHQL_QUERY, "variables": vars})
        .json()["data"]
        .get("Media", None)
    ):
        ro_title = animeResp["title"]["romaji"]
        na_title = animeResp["title"]["native"]
        en_title = animeResp["title"]["english"]
        
        title_parts = []
        if en_title:
            title_parts.append(en_title)
        if ro_title and ro_title != en_title:
            title_parts.append(ro_title)
        
        main_title = " | ".join(title_parts) if title_parts else (na_title or "Unknown Title")
        
        format_type = animeResp["format"].capitalize() if animeResp["format"] else "N/A"
        status = animeResp["status"].capitalize() if animeResp["status"] else "N/A"
        
        first_aired = "N/A"
        last_aired = "N/A"
        
        try:
            sd = animeResp["startDate"]
            if sd and sd["year"] and sd["month"] and sd["day"]:
                first_aired = f"{sd['year']}-{sd['month']}-{sd['day']}"
        except:
            pass
            
        try:
            ed = animeResp["endDate"]
            if ed and ed["year"] and ed["month"] and ed["day"]:
                last_aired = f"{ed['year']}-{ed['month']}-{ed['day']}"
        except:
            pass
        
        clean_genres = ", ".join(animeResp["genres"]) if animeResp["genres"] else "N/A"
        
        runtime = "N/A"
        if animeResp.get("duration"):
            runtime = f"{animeResp['duration']} minutes"
        
        episodes = animeResp.get("episodes", "N/A")
        average_rating = animeResp.get("averageScore", "N/A")
        
        description = animeResp.get("description", "")
        if description:
            description = description.replace("<br>", "\n").replace("<i>", "").replace("</i>", "")
            if len(description) > 400:
                description = f"{description[:400]}..."
        else:
            description = "No synopsis available."
        
        source = animeResp.get("source", "").replace("_", " ").title() if animeResp.get("source") else None
        
        template = f"**{main_title}**\n\n"
        template += f"**⧎ Genres :** {clean_genres}\n"
        template += f"**⧎ Type :** {format_type}\n"
        template += f"**⧎ Average Rating :** {average_rating}\n"
        template += f"**⧎ Status :** {status}\n"
        template += f"**⧎ First aired :** {first_aired}\n"
        template += f"**⧎ Last aired :** {last_aired}\n"
        template += f"**⧎ Runtime :** {runtime}\n"
        template += f"**⧎ No of episodes :** {episodes}\n\n"
        template += f"**⧎ Synopsis :**\n<blockquote>{description}</blockquote>"
        
        if source:
            template += f"\n\n(Source: {source})"

        siteurl = animeResp.get("siteUrl")
        trailer = animeResp.get("trailer", None)
        if trailer and trailer.get("site") == "youtube":
            trailer = f"https://youtu.be/{trailer.get('id')}"
        siteid = animeResp.get("id")
        title_img = f"https://img.anili.st/media/{siteid}"
        
        btns = ButtonMaker()
        btns.ubutton("🎬 AniList Info", siteurl)
        if trailer:
            btns.ubutton("🎞 Trailer", trailer)
        btns.ibutton("📑 Reviews", f"anime {user_id} rev {siteid}")
        btns.ibutton("🎯 Tags", f"anime {user_id} tags {siteid}")
        btns.ibutton("🧬 Relations", f"anime {user_id} rel {siteid}")
        btns.ibutton("👥 Characters", f"anime {user_id} cha {siteid}")
        btns.ibutton("📊 Streaming Sites", f"anime {user_id} sts {siteid}")
        
        if aniid:
            return template, btns.build_menu(2)
        try:
            await sendMessage(msg, template, btns.build_menu(2), photo=title_img)
        except Exception:
            await sendMessage(
                msg,
                template,
                btns.build_menu(2),
                photo="https://te.legra.ph/file/8a5155c0fc61cc2b9728c.jpg",
            )


async def setAnimeButtons(client, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    siteid = data[3]
    btns = ButtonMaker()
    btns.ibutton("⌫ Back", f"anime {data[1]} home {siteid}")
    if user_id != int(data[1]):
        await query.answer(text="Not Yours!", show_alert=True)
        return
    await query.answer()
    if data[2] == "tags":
        aniTag = (
            rpost(url, json={"query": ANIME_GRAPHQL_QUERY, "variables": {"id": siteid}})
            .json()["data"]
            .get("Media", None)
        )
        msg = "**Tags :**\n\n" + "\n".join(
            f"""<a href="https://anilist.co/search/anime?genres={q(x['name'])}">{x['name']}</a> {x['rank']}%"""
            for x in aniTag["tags"]
        )
    elif data[2] == "sts":
        links = (
            rpost(url, json={"query": ANIME_GRAPHQL_QUERY, "variables": {"id": siteid}})
            .json()["data"]
            .get("Media", None)
        )
        msg = "**External & Streaming Links :**\n\n" + "\n".join(
            f"""<a href="{x['url']}">{x['site']}</a>""" for x in links["externalLinks"]
        )
    elif data[2] == "rev":
        animeResp = (
            rpost(url, json={"query": ANIME_GRAPHQL_QUERY, "variables": {"id": siteid}})
            .json()["data"]
            .get("Media", None)
        )
        reList = animeResp["reviews"]["nodes"]
        msg = "**Reviews :**\n\n" + "\n\n".join(
            f"""<a href="{x['siteUrl']}">{x['summary']}</a>\n**Score :** `{x['score']} / 100`\n*By {x['user']['name']}*"""
            for x in reList[:8]
        )
    elif data[2] == "rel":
        animeResp = (
            rpost(url, json={"query": ANIME_GRAPHQL_QUERY, "variables": {"id": siteid}})
            .json()["data"]
            .get("Media", None)
        )
        msg = "**Relations :**\n\n" + "\n\n".join(
            f"""<a href="{x['node']['siteUrl']}">{x['node']['title']['english']}</a> ({x['node']['title']['romaji']})\n**Format**: `{x['node']['format'].capitalize()}`\n**Status**: `{x['node']['status'].capitalize()}`\n**Average Score**: `{x['node']['averageScore']}%`\n**Source**: `{x['node']['source'].capitalize()}`\n**Relation Type**: `{x.get('relationType', 'N/A').capitalize()}`"""
            for x in animeResp["relations"]["edges"]
        )
    elif data[2] == "cha":
        animeResp = (
            rpost(url, json={"query": ANIME_GRAPHQL_QUERY, "variables": {"id": siteid}})
            .json()["data"]
            .get("Media", None)
        )
        msg = "**List of Characters :**\n\n" + "\n\n".join(
            f"""• <a href="{x['node']['siteUrl']}">{x['node']['name']['full']}</a> ({x['node']['name']['native']})\n**Role :** {x['role'].capitalize()}"""
            for x in (animeResp["characters"]["edges"])[:8]
        )
    elif data[2] == "home":
        msg, btns = await anilist(client, message, siteid, data[1])
        await editMessage(message, msg, btns)
        return
    await editMessage(message, msg, btns.build_menu(1))
    return


async def character(_, message, aniid=None, u_id=None):
    global sptext
    rlp_mk = None
    if not aniid:
        search = message.text.split(" ", 1)
        if len(search) == 1:
            await sendMessage(
                message,
                "**Format :**\n`/character` *[search AniList Character]*",
            )
            return
        vars = {"search": search[1]}
        user_id = message.from_user.id
    else:
        vars = {"id": aniid}
        user_id = int(u_id)
    if (
        json := rpost(url, json={"query": character_query, "variables": vars})
        .json()["data"]
        .get("Character", None)
    ):
        msg = f"**{json.get('name').get('full')}** (`{json.get('name').get('native')}`)\n\n"
        description = json["description"]
        site_url = json.get("siteUrl")
        siteid = json.get("id")
        if "~!" in description and "!~" in description:
            btn = ButtonMaker()
            sptext = (
                description.split("~!", 1)[1]
                .rsplit("!~", 1)[0]
                .replace("~!", "")
                .replace("!~", "")
            )
            btn.ibutton("🔍 View Spoiler", f"cha {user_id} spoil {siteid}")
            rlp_mk = btn.build_menu(1)
            description = description.split("~!", 1)[0]
        if len(description) > 700:
            description = f"{description[:700]}...."
        msg += f"<blockquote>{markdown(description).replace('<p>', '').replace('</p>', '')}</blockquote>"
        if image := json.get("image", None):
            img = image.get("large")
        if aniid:
            return msg, rlp_mk
        if img:
            await sendMessage(message, msg, rlp_mk, img)
        else:
            await sendMessage(message, msg)


async def setCharacButtons(client, query):
    global sptext
    message = query.message
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    btns = ButtonMaker()
    btns.ibutton("⌫ Back", f"cha {data[1]} home {data[3]}")
    if user_id != int(data[1]):
        await query.answer(text="Not Yours!", show_alert=True)
        return
    elif data[2] == "spoil":
        await query.answer("Alert !! Shh")
        if len(sptext) > 900:
            sptext = f"{sptext[:900]}..."
        await editMessage(
            message,
            f"**Spoiler Ahead :**\n\n<tg-spoiler><blockquote>{markdown(sptext).replace('<p>', '').replace('</p>', '')}</blockquote></tg-spoiler>",
            btns.build_menu(1),
        )
    elif data[2] == "home":
        await query.answer()
        msg, btns = await character(client, message, data[3], data[1])
        await editMessage(message, msg, btns)


async def manga(_, message):
    search = message.text.split(" ", 1)
    if len(search) == 1:
        await sendMessage(
            message, "**Format :**\n`/manga` *[search manga]*"
        )
        return
    search = search[1]
    variables = {"search": search}
    json = (
        rpost(url, json={"query": manga_query, "variables": variables})
        .json()["data"]
        .get("Media", None)
    )
    msg = ""
    if json:
        title, title_native = json["title"].get("romaji", False), json["title"].get(
            "native", False
        )
        start_date, status, score = (
            json["startDate"].get("year", False),
            json.get("status", False),
            json.get("averageScore", False),
        )
        if title:
            msg += f"**{title}**"
            if title_native:
                msg += f"(`{title_native}`)"
        if start_date:
            msg += f"\n**Start Date** - `{start_date}`"
        if status:
            msg += f"\n**Status** - `{status}`"
        if score:
            msg += f"\n**Score** - `{score}`"
        msg += "\n**Genres** - "
        for x in json.get("genres", []):
            msg += f"#{x}, "
        msg = msg[:-2]
        info = json["siteUrl"]
        buttons = ButtonMaker()
        buttons.ubutton("🎬 AniList Info", info)
        bimage = json.get("bannerImage", False)
        image = f"https://img.anili.st/media/{json.get('id')}"
        description = json.get('description', 'No description available.')
        msg += f"\n\n<blockquote>{description}</blockquote>"
        msg = msg.replace("<br>", "").replace("<i>", "").replace("</i>", "")
        try:
            await sendMessage(message, msg, buttons.build_menu(1), image)
        except Exception:
            msg += f" [〽️]({image})"
            await sendMessage(message, msg, buttons.build_menu(1))


async def anime_help(_, message):
    help_string = """
**🔍 Anime Help Guide**
• `/anime` : *[search AniList]*
• `/character` : *[search AniList Character]*
• `/manga` : *[search manga]*"""
    await sendMessage(message, help_string)


bot.add_handler(
    MessageHandler(
        anilist,
        filters=command(BotCommands.AniListCommand)
        & CustomFilters.authorized
        & ~CustomFilters.blacklisted,
    )
)
bot.add_handler(
    MessageHandler(
        character,
        filters=command("character")
        & CustomFilters.authorized
        & ~CustomFilters.blacklisted,
    )
)
bot.add_handler(
    MessageHandler(
        manga,
        filters=command("manga")
        & CustomFilters.authorized
        & ~CustomFilters.blacklisted,
    )
)
bot.add_handler(
    MessageHandler(
        anime_help,
        filters=command(BotCommands.AnimeHelpCommand)
        & CustomFilters.authorized
        & ~CustomFilters.blacklisted,
    )
)
bot.add_handler(CallbackQueryHandler(setAnimeButtons, filters=regex(r"^anime")))
bot.add_handler(CallbackQueryHandler(setCharacButtons, filters=regex(r"^cha")))
