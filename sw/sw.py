from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core import commands, checks
import discord
import aiohttp
import json


class SW(commands.Cog):
    """Interact with the Star Wars API"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.__unload()

    def __unload(self):
        self.session.detach()

    @checks.bot_has_permissions(embed_links=True)
    @commands.group(name="swapi", aliases=["starwars"])
    async def starwars(self, ctx):
        """Group command for interacting with the Star Wars API"""
        pass

    @starwars.command()
    async def person(self, ctx, person_id: int):
        """Gets the profile of a person by their ID"""
        async with ctx.typing():
            response = await self.session.get(r"https://swapi.co/api/people/" + str(person_id))
            if response.status == 404:
                return await ctx.send("Invalid Person ID.")
            person = json.loads(await response.text())
            embed = discord.Embed(title=f"Person: {person['name']}", color=0x32CD32)
            embed.add_field(name="ID:", value=str(person_id))
            for key, value in person.items():
                if key in [
                    "name",
                    "homeworld",
                    "films",
                    "species",
                    "vehicles",
                    "starships",
                    "created",
                    "edited",
                    "url",
                ]:
                    continue
                embed.add_field(name=key.replace("_", " ").title(), value=value.title())
            homeworld_num = int(person["homeworld"].split(r"/")[-2])
            homeworld = await self.session.get(person["homeworld"])
            homeworld = json.loads(await homeworld.text())
            embed.add_field(
                name="Homeworld", value=f"Name: {homeworld['name']}; ID: {str(homeworld_num)}"
            )
            films = []
            for film in person["films"]:
                film_num = int(film.split(r"/")[-2])
                response = await self.session.get(film)
                film = json.loads(await response.text())
                films.append(f"Title: {film['title']}; ID: {str(film_num)}")
            if len(films) != 0:
                embed.add_field(name="Films:", value="\n".join(films))
            species_num = int(person["species"][0].split(r"/")[-2])
            species = await self.session.get(person["species"][0])
            species = json.loads(await species.text())
            embed.add_field(
                name="Species", value=f"Name: {species['name']}; ID: {str(species_num)}"
            )
            vehicles = []
            for vehicle in person["vehicles"]:
                vehicle_num = int(vehicle.split(r"/")[-2])
                response = await self.session.get(vehicle)
                vehicle = json.loads(await response.text())
                vehicles.append(f"Name: {vehicle['name']}; ID: {str(vehicle_num)}")
            if len(vehicles) != 0:
                embed.add_field(name="Vehicles:", value="\n".join(vehicles))
            starships = []
            for starship in person["starships"]:
                starship_num = int(starship.split(r"/")[-2])
                response = await self.session.get(starship)
                starship = json.loads(await response.text())
                starships.append(f"Name: {starship['name']}; ID: {str(starship_num)}")
            if len(starships) != 0:
                embed.add_field(name="Starships:", value="\n".join(starships))
            await ctx.send(embed=embed)

    @starwars.command()
    async def planet(self, ctx, planet_id: int):
        """Gets the profile of a planet by their ID"""
        async with ctx.typing():
            response = await self.session.get(r"https://swapi.co/api/planets/" + str(planet_id))
            if response.status == 404:
                return await ctx.send("Invalid Planet ID.")
            planet = json.loads(await response.text())
            embed = discord.Embed(title=f"Planet: {planet['name']}", color=0x800080)
            embed.add_field(name="ID:", value=str(planet_id))
            for key, value in planet.items():
                if key in ["name", "residents", "films", "edited", "created", "url"]:
                    continue
                embed.add_field(name=key.replace("_", " ").title(), value=value.title())
            films = []
            for film in planet["films"]:
                film_num = int(film.split(r"/")[-2])
                response = await self.session.get(film)
                film = json.loads(await response.text())
                films.append(f"Title: {film['title']}; ID: {str(film_num)}")
            if len(films) != 0:
                embed.add_field(name="Films:", value="\n".join(films))
            residents = []
            for resident in planet["residents"]:
                resident_num = int(resident.split(r"/")[-2])
                response = await self.session.get(resident)
                resident = json.loads(await response.text())
                residents.append(f"Name: {resident['name']}; ID: {str(resident_num)}")
            if len(residents) != 0:
                embed.add_field(name="Residents:", value="\n".join(residents))
            await ctx.send(embed=embed)

    @starwars.command()
    async def film(self, ctx, film_id: int):
        """Gets the info about a film by their ID"""
        async with ctx.typing():
            response = await self.session.get(r"https://swapi.co/api/films/" + str(film_id))
            if response.status == 404:
                return await ctx.send("Invalid Film ID.")
            film = json.loads(await response.text())
            embed = discord.Embed(title=f"Film: {film['title']}; Page 1/4", color=0x0000FF)
            embed.add_field(name="ID:", value=str(film_id))
            for key, value in film.items():
                if key in [
                    "name",
                    "characters",
                    "planets",
                    "starships",
                    "vehicles",
                    "species",
                    "created",
                    "edited",
                    "url",
                    "opening_crawl",
                ]:
                    continue
                value = value.title() if hasattr(value, "title") else value
                embed.add_field(name=key.replace("_", " ").title(), value=value)
            embed2 = discord.Embed(title=f"Film: {film['title']}; Page 2/4", color=0x0000FF)
            embed2.add_field(name="Opening Crawl", value=film["opening_crawl"])
            embed3 = discord.Embed(title=f"Film: {film['title']}; Page 3/4", color=0x0000FF)
            residents = []
            for resident in film["characters"]:
                resident_num = int(resident.split(r"/")[-2])
                response = await self.session.get(resident)
                resident = json.loads(await response.text())
                residents.append(f"Name: {resident['name']}; ID: {str(resident_num)}")
            if len(residents) != 0:
                embed3.add_field(name="Characters:", value="\n".join(residents))
            planets = []
            for planet in film["planets"]:
                planet_num = int(planet.split(r"/")[-2])
                response = await self.session.get(planet)
                planet = json.loads(await response.text())
                planets.append(f"Name: {planet['name']}; ID: {str(planet_num)}")
            if len(planets) != 0:
                embed3.add_field(name="Planets:", value="\n".join(planets))
            embed4 = discord.Embed(title=f"Film: {film['title']}; Page 4/4", color=0x0000FF)
            objects = []
            for entry in film["starships"]:
                entry_num = int(entry.split(r"/")[-2])
                response = await self.session.get(entry)
                entry = json.loads(await response.text())
                objects.append(f"Name: {entry['name']}; ID: {str(entry_num)}")
            if len(objects) != 0:
                embed4.add_field(name="Starships:", value="\n".join(objects))
            objects = []
            for entry in film["vehicles"]:
                entry_num = int(entry.split(r"/")[-2])
                response = await self.session.get(entry)
                entry = json.loads(await response.text())
                objects.append(f"Name: {entry['name']}; ID: {str(entry_num)}")
            if len(objects) != 0:
                embed4.add_field(name="Vehicles:", value="\n".join(objects))
            objects = []
            for entry in film["species"]:
                entry_num = int(entry.split(r"/")[-2])
                response = await self.session.get(entry)
                entry = json.loads(await response.text())
                objects.append(f"Name: {entry['name']}; ID: {str(entry_num)}")
            if len(objects) != 0:
                embed4.add_field(name="Species:", value="\n".join(objects))
            embeds = [embed, embed2, embed3, embed4]
            await menu(ctx, embeds, DEFAULT_CONTROLS)

    @starwars.command()
    async def starship(self, ctx, starship_id: int):
        """Gets the profile of a starship by its ID"""
        async with ctx.typing():
            response = await self.session.get(
                r"https://swapi.co/api/starships/" + str(starship_id)
            )
            if response.status == 404:
                return await ctx.send("Invalid Starship ID.")
            starship = json.loads(await response.text())
            embed = discord.Embed(title=f"Starship: {starship['name']}", color=0x000000)
            embed.add_field(name="ID:", value=str(starship_id))
            for key, value in starship.items():
                if key in ["name", "films", "edited", "created", "url", "pilots"]:
                    continue
                embed.add_field(name=key.replace("_", " ").title(), value=value.title())
            objects = []
            for entry in starship["films"]:
                entry_num = int(entry.split(r"/")[-2])
                response = await self.session.get(entry)
                entry = json.loads(await response.text())
                objects.append(f"Name: {entry['title']}; ID: {str(entry_num)}")
            if len(objects) != 0:
                embed.add_field(name="Films:", value="\n".join(objects))
            objects = []
            for entry in starship["pilots"]:
                entry_num = int(entry.split(r"/")[-2])
                response = await self.session.get(entry)
                entry = json.loads(await response.text())
                objects.append(f"Name: {entry['name']}; ID: {str(entry_num)}")
            if len(objects) != 0:
                embed.add_field(name="Pilots:", value="\n".join(objects))
            await ctx.send(embed=embed)

    @starwars.command()
    async def vehicle(self, ctx, vehicle_id: int):
        """Gets the profile of a vehicle by its ID"""
        async with ctx.typing():
            response = await self.session.get(r"https://swapi.co/api/vehicles/" + str(vehicle_id))
            if response.status == 404:
                return await ctx.send("Invalid Vehicle ID.")
            vehicle = json.loads(await response.text())
            embed = discord.Embed(title=f"Vehicle: {vehicle['name']}", color=0x228B22)
            embed.add_field(name="ID:", value=str(vehicle_id))
            for key, value in vehicle.items():
                if key in ["name", "films", "edited", "created", "url", "pilots"]:
                    continue
                embed.add_field(name=key.replace("_", " ").title(), value=value.title())
            objects = []
            for entry in vehicle["films"]:
                entry_num = int(entry.split(r"/")[-2])
                response = await self.session.get(entry)
                entry = json.loads(await response.text())
                objects.append(f"Name: {entry['title']}; ID: {str(entry_num)}")
            if len(objects) != 0:
                embed.add_field(name="Films:", value="\n".join(objects))
            objects = []
            for entry in vehicle["pilots"]:
                entry_num = int(entry.split(r"/")[-2])
                response = await self.session.get(entry)
                entry = json.loads(await response.text())
                objects.append(f"Name: {entry['name']}; ID: {str(entry_num)}")
            if len(objects) != 0:
                embed.add_field(name="Pilots:", value="\n".join(objects))
            await ctx.send(embed=embed)

    @starwars.command()
    async def species(self, ctx, species_id: int):
        """Gets the profile of a species by its ID"""
        async with ctx.typing():
            response = await self.session.get(r"https://swapi.co/api/species/" + str(species_id))
            if response.status == 404:
                return await ctx.send("Invalid Species ID.")
            species = json.loads(await response.text())
            embed = discord.Embed(title=f"Species: {species['name']}", color=0xD2B48C)
            embed.add_field(name="ID:", value=str(species_id))
            for key, value in species.items():
                if key in ["name", "homeworld", "films", "people", "edited", "created", "url"]:
                    continue
                embed.add_field(name=key.replace("_", " ").title(), value=value.title())
            homeworld_num = int(species["homeworld"].split(r"/")[-2])
            homeworld = await self.session.get(species["homeworld"])
            homeworld = json.loads(await homeworld.text())
            embed.add_field(
                name="Homeworld", value=f"Name: {homeworld['name']}; ID: {str(homeworld_num)}"
            )
            objects = []
            for entry in species["films"]:
                entry_num = int(entry.split(r"/")[-2])
                response = await self.session.get(entry)
                entry = json.loads(await response.text())
                objects.append(f"Name: {entry['title']}; ID: {str(entry_num)}")
            if len(objects) != 0:
                embed.add_field(name="Films:", value="\n".join(objects))
            objects = []
            for entry in species["people"]:
                entry_num = int(entry.split(r"/")[-2])
                response = await self.session.get(entry)
                entry = json.loads(await response.text())
                objects.append(f"Name: {entry['name']}; ID: {str(entry_num)}")
            if len(objects) != 0:
                embed.add_field(name="People:", value="\n".join(objects))
            await ctx.send(embed=embed)

    @starwars.group(name="all")
    async def _all_group(self, ctx):
        """Get all people, planets, starships, vehicles, species or films of star wars"""
        pass

    @_all_group.command()
    async def people(self, ctx):
        """Grabs all people in the star wars API.
        
        This command does take a bit."""
        async with ctx.typing():
            data = []
            query = "https://swapi.co/api/people"
            while True:
                response = await self.session.get(query)
                text = json.loads(await response.text())
                data_two = text["results"]
                data += data_two
                if bool(text["next"]):
                    query = text["next"]
                else:
                    break
            persons_list = []
            for person in data:
                embed = discord.Embed(title=f"Person: {person['name']}", color=0x32CD32)
                num = int(person["url"].split(r"/")[-2])
                embed.add_field(name="ID:", value=str(num))
                for key, value in person.items():
                    if key in [
                        "name",
                        "homeworld",
                        "films",
                        "species",
                        "vehicles",
                        "starships",
                        "created",
                        "edited",
                        "url",
                    ]:
                        continue
                    embed.add_field(name=key.replace("_", " ").title(), value=value.title())
                homeworld_num = int(person["homeworld"].split(r"/")[-2])
                embed.add_field(name="Homeworld", value=f"ID: {str(homeworld_num)}")
                persons_list.append(embed)
            persons_list.sort(
                key=lambda x: int(
                    [field for field in x.to_dict()["fields"] if field["name"] == "ID:"][0][
                        "value"
                    ]
                )
            )
        await menu(ctx, persons_list, DEFAULT_CONTROLS)

    @_all_group.command()
    async def planets(self, ctx):
        """Grabs all planets in the star wars API.
        
        This command does take a bit."""
        async with ctx.typing():
            data = []
            query = "https://swapi.co/api/planets"
            while True:
                response = await self.session.get(query)
                text = json.loads(await response.text())
                data_two = text["results"]
                data += data_two
                if bool(text["next"]):
                    query = text["next"]
                else:
                    break
            planets_list = []
            for planet in data:
                embed = discord.Embed(title=f"Planet: {planet['name']}", color=0x800080)
                num = int(planet["url"].split(r"/")[-2])
                embed.add_field(name="ID:", value=str(num))
                for key, value in planet.items():
                    if key in ["name", "residents", "films", "edited", "created", "url"]:
                        continue
                    embed.add_field(name=key.replace("_", " ").title(), value=value.title())
                planets_list.append(embed)
            planets_list.sort(
                key=lambda x: int(
                    [field for field in x.to_dict()["fields"] if field["name"] == "ID:"][0][
                        "value"
                    ]
                )
            )
        await menu(ctx, planets_list, DEFAULT_CONTROLS)

    @_all_group.command()
    async def films(self, ctx):
        """Grabs all films in the star wars API.
        
        This command does take a bit."""
        async with ctx.typing():
            data = []
            query = "https://swapi.co/api/films"
            while True:
                response = await self.session.get(query)
                text = json.loads(await response.text())
                data_two = text["results"]
                data += data_two
                if bool(text["next"]):
                    query = text["next"]
                else:
                    break
            films_list = []
            for film in data:
                embed = discord.Embed(title=f"Film: {film['title']}", color=0xD2B48C)
                num = int(film["url"].split(r"/")[-2])
                embed.add_field(name="ID:", value=str(num))
                for key, value in film.items():
                    if key in [
                        "name",
                        "characters",
                        "planets",
                        "starships",
                        "vehicles",
                        "species",
                        "created",
                        "edited",
                        "url",
                        "opening_crawl",
                    ]:
                        continue
                    value = value.title() if hasattr(value, "title") else value
                    embed.add_field(name=key.replace("_", " ").title(), value=value)
                films_list.append(embed)
            films_list.sort(
                key=lambda x: int(
                    [field for field in x.to_dict()["fields"] if field["name"] == "ID:"][0][
                        "value"
                    ]
                )
            )
        await menu(ctx, films_list, DEFAULT_CONTROLS)

    @_all_group.command()
    async def starships(self, ctx):
        """Grabs all starships in the star wars API.
        
        This command does take a bit."""
        async with ctx.typing():
            data = []
            query = "https://swapi.co/api/starships"
            while True:
                response = await self.session.get(query)
                text = json.loads(await response.text())
                data_two = text["results"]
                data += data_two
                if bool(text["next"]):
                    query = text["next"]
                else:
                    break
            starships_list = []
            for starship in data:
                embed = discord.Embed(title=f"Starship: {starship['name']}", color=0x000000)
                num = int(starship["url"].split(r"/")[-2])
                embed.add_field(name="ID:", value=str(num))
                for key, value in starship.items():
                    if key in ["name", "films", "edited", "created", "url", "pilots"]:
                        continue
                    value = value.title() if hasattr(value, "title") else value
                    embed.add_field(name=key.replace("_", " ").title(), value=value)
                starships_list.append(embed)
            starships_list.sort(
                key=lambda x: int(
                    [field for field in x.to_dict()["fields"] if field["name"] == "ID:"][0][
                        "value"
                    ]
                )
            )
        await menu(ctx, starships_list, DEFAULT_CONTROLS)

    @_all_group.command()
    async def vehicles(self, ctx):
        """Grabs all vehicles in the star wars API.
        
        This command does take a bit."""
        async with ctx.typing():
            data = []
            query = "https://swapi.co/api/vehicles"
            while True:
                response = await self.session.get(query)
                text = json.loads(await response.text())
                data_two = text["results"]
                data += data_two
                if bool(text["next"]):
                    query = text["next"]
                else:
                    break
            vehicles_list = []
            for vehicle in data:
                embed = discord.Embed(title=f"Vehicle: {vehicle['name']}", color=0x228B22)
                num = int(vehicle["url"].split(r"/")[-2])
                embed.add_field(name="ID:", value=str(num))
                for key, value in vehicle.items():
                    if key in ["name", "films", "edited", "created", "url", "pilots"]:
                        continue
                    value = value.title() if hasattr(value, "title") else value
                    embed.add_field(name=key.replace("_", " ").title(), value=value)
                vehicles_list.append(embed)
            vehicles_list.sort(
                key=lambda x: int(
                    [field for field in x.to_dict()["fields"] if field["name"] == "ID:"][0][
                        "value"
                    ]
                )
            )
        await menu(ctx, vehicles_list, DEFAULT_CONTROLS)

    @_all_group.command(name="species")
    async def _all_species(self, ctx):
        """Grabs all vehicles in the star wars API.
        
        This command does take a bit."""
        async with ctx.typing():
            data = []
            query = "https://swapi.co/api/species"
            while True:
                response = await self.session.get(query)
                text = json.loads(await response.text())
                data_two = text["results"]
                data += data_two
                if bool(text["next"]):
                    query = text["next"]
                else:
                    break
            species_list = []
            for species in data:
                embed = discord.Embed(title=f"Species: {species['name']}", color=0xD2B48C)
                num = int(species["url"].split(r"/")[-2])
                embed.add_field(name="ID:", value=str(num))
                for key, value in species.items():
                    if key in ["name", "homeworld", "films", "people", "edited", "created", "url"]:
                        continue
                    value = value.title() if hasattr(value, "title") else value
                    embed.add_field(name=key.replace("_", " ").title(), value=value)
                species_list.append(embed)
            species_list.sort(
                key=lambda x: int(
                    [field for field in x.to_dict()["fields"] if field["name"] == "ID:"][0][
                        "value"
                    ]
                )
            )
        await menu(ctx, species_list, DEFAULT_CONTROLS)
