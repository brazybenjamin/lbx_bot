import discord
from discord.ext import commands, menus
import motor.motor_asyncio as motor
from utils.diary import get_lid
from config import SETTINGS, conn_url

prefix = SETTINGS['prefix']

def get_conn_url(db_name):
    return conn_url + db_name + '?retryWrites=true&w=majority'


class Follow(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(help=f'''Follow your diary. Takes your LB username as input.
    Must set a channel using ``{prefix}setchan`` for entries to start popping.
    Examples:\n1. To add yourself if your Letterboxd username is 'mp4' (you don't need to be a mod): ``{prefix}follow mp4``
    2.To add someone besides you, you need to ping them too: ``{prefix}follow mp4 @chieko``''')
    async def follow(self, ctx, lb_id, member: discord.Member = None):
        db_name = f'g{ctx.guild.id}'
        client = motor.AsyncIOMotorClient(get_conn_url(db_name))
        db = client[db_name]
        users = db.users

        member = member or ctx.author
        try:
            conn = await self.db.acquire()
            async with conn.transaction():
                lid = await get_lid(self.bot.lbx, lb_id)
                chan_id = await conn.fetchval(f'SELECT channel_id FROM public.guilds WHERE id={ctx.guild.id}')
                await self.db.execute(f'''INSERT INTO {db_name}.users (uid, lb_id, lid)
                                     VALUES ({member.id}, $1, $2)''', lb_id, lid)
            user = {
                "uid": member.id,
                "lb_id": lb_id,
                'lid': lid
            }
            await users.update_one({"lb_id": user["lb_id"]}, {"$set": user}, upsert=True)

            await ctx.send(f"Added {lb_id}.")
            await self.bot.get_cog('Ratings').usync(ctx, member)
        except Exception as e:
            print(e)
            await ctx.send('Error, maybe user already exists')
        finally:
            await self.db.release(conn)



    @commands.command(help='Unfollow user diary')
    async def unfollow(self, ctx, lb_id):
        conn = await self.db.acquire()
        async with conn.transaction():
            await self.db.execute(f'''DELETE FROM g{ctx.guild.id}.users
                                    WHERE lb_id='{lb_id}'
                                ''')
        await self.db.release(conn)
        await ctx.send(f"Removed {lb_id}.")


    @commands.command(aliases=['setchan'], help='Set the channel where updates appear.')
    @commands.has_guild_permissions(manage_channels=True)
    async def setchannel(self, ctx, channel: discord.TextChannel):
        conn = await self.db.acquire()
        async with conn.transaction():
            print(f'UPDATE public.guilds SET channel_id={channel.id} WHERE id={ctx.guild.id}')
            await self.db.execute(f'UPDATE public.guilds SET channel_id={channel.id} WHERE id={ctx.guild.id}')
        await self.db.release(conn)
        await ctx.send(f'Now following updates in {channel.mention}')

    @commands.command(help='List followed users', aliases=[f'{prefix}follow'])
    async def following(self, ctx):
        follow_str = ''
        conn = await self.db.acquire()
        async with conn.transaction():
            async for row in conn.cursor(f'SELECT lb_id, uid FROM g{ctx.guild.id}.users'):
                user = self.bot.get_user(row[1])
                display_name = row[0] if not user else user.display_name
                follow_str += f'[{display_name}](https://letterboxd.com/{row[0]}), '

        chan_id = await conn.fetchval(f'SELECT channel_id FROM public.guilds WHERE id={ctx.guild.id}')
        await self.db.release(conn)

        embed = None
        if not chan_id:
           await ctx.send(f"No follow channel set. Will not post updates. See {prefix}help setchan for details.")
           embed = discord.Embed(
               description=f'Will sync the following users on {prefix}ssync:\n{follow_str}'
           )
        else:
            embed = discord.Embed(
            description=f'Following these users in {self.bot.get_channel(chan_id).mention}\n' + follow_str[:-2]
        )
        await ctx.send(embed=embed)


    @setchannel.error
    async def setchannel_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingPermissions):
            await ctx.send('Not...for you.')


def setup(bot):
    bot.add_cog(Follow(bot))
