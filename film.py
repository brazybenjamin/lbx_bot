import discord
import json


def get_film_embed(lbx, film_keywords, verbosity=0):
    film = get_search_result(lbx, film_keywords)
    if not film:
        return None
    film_instance = lbx.film(film['id'])
    film_details = film_instance.details()
    film_stats = film_instance.statistics()

    print(json.dumps(film_details, sort_keys=True, indent=4))
    print(json.dumps(film_stats, sort_keys=True, indent=4))

    embed = discord.Embed(
        title=f"{film_details['name']} ({film_details['releaseYear']})",
        url=get_link(film_details),
        description=get_description(film_details, film_stats, verbosity),
    )

    if 'poster' in film_details:
        embed.set_thumbnail(url=film_details['poster']['sizes'][-1]['url'])
    return embed


def get_link(film_details):
    for link in film_details['links']:
        if link['type'] == 'letterboxd':
            return link['url']


def get_description(film_details, film_stats, verbosity=0):
    description = ''
    if 'originalName' in film_details:
        description += f"_{film_details['originalName']}_\n"

    director_str = '**'
    for contribution in film_details['contributions']:
        if contribution['type'] == 'Director':
            for director in contribution['contributors']:
                director_str += director['name'] + ', '

    description += director_str[:-2] + '.** '

    country_str = ''
    if 'countries' in film_details:
        for count_ry, country in enumerate(film_details['countries']):
            if count_ry == 3:
                break
            if verbosity == 0 and count_ry == 2:
                break
            country_str += country['name'] + ', '

        description += country_str[:-2]

    if 'rating' in film_stats:
        description += f"\n**{round(film_stats['rating'], 2)}** from "
        description += f"{human_count(film_stats['counts']['ratings'])} ratings, "
    else:
        description += '\n'
    description += f"{human_count(film_stats['counts']['watches'])} watched"

    if 'runTime' in film_details:
        runtime = film_details['runTime']
        hours = runtime // 60
        minutes = runtime % 60
        if hours > 0:
            description += f'\n**{hours} h {minutes} min.** '
        else:
            description += f'**{runtime} min.** '

    if 'genres' in film_details:
        genre_str = ''
        for genre in film_details['genres']:
            genre_str += genre['name'] + ', '
        description += genre_str[:-2]
    if verbosity > 0:
        description += '\n```' + film_details['description'] + '```\n'

    return description


def get_search_result(lbx, film_keywords):
    search_request = {
        'perPage': 1,
        'input': film_keywords,
        'include': 'FilmSearchItem'
    }

    search_response = lbx.search(search_request=search_request)

    # print(json.dumps(search_response, sort_keys=True, indent=4))
    if not search_response['items']:
        return None
    return search_response['items'][0]['film']


def human_count(n):
    m = n / 1000
    if m >= 1:
        return f'{round(m, 1)}k'
    else:
        return n
