"""Sample data for the SAMPLE workbook: 12 shows over Aug–Oct 2026 and item rows for two shows.

The numbers are invented but realistic for a small Whatnot seller. Show 7 loses money (too many giveaways) and
show 7 also runs past midnight, so both cases appear in the screenshots and tests.
"""
import datetime as dt

D, T = dt.date, dt.time


def show(date, title, cat, slot, fmt, start, end, gross, orders, ship, cogs, gives, gover, supplies, other, viewers, notes=""):
    return dict(date=date, title=title, cat=cat, slot=slot, fmt=fmt, start=start, end=end, gross=gross, orders=orders,
                ship=ship, cogs=cogs, gives=gives, gover=gover, supplies=supplies, other=other, viewers=viewers, notes=notes)


SHOWS = [
    show(D(2026, 8, 4), "Tuesday Night Breaks", "Sports Cards", "Evening", "Auction", T(19, 0), T(21, 30),
         1240.00, 38, 142.00, 610.00, 6, None, 24.50, None, 85),
    show(D(2026, 8, 9), "Sunday Sneaker Drop", "Sneakers", "Afternoon", "Buy It Now", T(13, 0), T(15, 0),
         2180.00, 9, 99.00, 1490.00, 2, None, 31.00, 15.00, 62, "Item list on ITEM SALES"),
    show(D(2026, 8, 15), "Pokemon Pack Night", "Pokemon/TCG", "Evening", "Mixed", T(20, 0), T(23, 0),
         965.00, 41, None, 470.00, 10, None, 18.00, None, 140),
    show(D(2026, 8, 27), "Thrift Haul Clothing", "Clothing", "Morning", "Auction", T(9, 30), T(11, 30),
         410.00, 23, None, 120.00, 5, None, 22.00, None, 34, "Slow start"),
    show(D(2026, 9, 1), "Tuesday Night Breaks", "Sports Cards", "Evening", "Auction", T(19, 0), T(21, 45),
         1385.00, 44, 160.00, 690.00, 6, None, 26.00, None, 92),
    show(D(2026, 9, 6), "Vintage Tees Sunday", "Vintage", "Afternoon", "Auction", T(14, 0), T(16, 30),
         720.00, 27, None, 240.00, 4, None, 19.50, None, 48),
    show(D(2026, 9, 12), "Mystery Pack Saturday", "Mystery Packs", "Late night", "Auction", T(22, 30), T(0, 30),
         540.00, 36, None, 380.00, 15, 96.00, 21.00, None, 160, "Too many giveaways"),
    show(D(2026, 9, 24), "Beauty Restock Live", "Beauty", "Evening", "Buy It Now", T(18, 30), T(20, 0),
         615.00, 31, None, 290.00, 3, None, 27.00, None, 41),
    show(D(2026, 10, 3), "Pokemon Pack Night", "Pokemon/TCG", "Evening", "Mixed", T(20, 0), T(23, 15),
         1150.00, 49, None, 560.00, 12, None, 21.00, None, 175),
    show(D(2026, 10, 6), "Tuesday Night Breaks", "Sports Cards", "Evening", "Auction", T(19, 0), T(21, 30),
         1510.00, 47, 175.00, 760.00, 6, None, 27.50, 25.00, 101, "New card sleeves"),
    show(D(2026, 10, 18), "Collectibles Sunday Brunch", "Collectibles", "Morning", "Auction", T(10, 0), T(12, 0),
         830.00, 22, None, 395.00, 4, None, 16.00, None, 39),
    show(D(2026, 10, 24), "Late Night Toy Auction", "Toys", "Late night", "Auction", T(22, 0), T(23, 45),
         495.00, 29, None, 260.00, 8, None, 17.50, None, 66),
]

# ITEM SALES: (show date, show title, item, category, item cost, sold price, buyer, shipped)
_SNEAKERS = [("Jordan 1 Retro High OG", 230, 340, "kicksbyjay", "Y"), ("Nike Dunk Low Panda", 90, 135, "solecollector21", "Y"),
             ("Yeezy Boost 350 V2", 185, 260, "mia_resells", "Y"), ("New Balance 550", 95, 145, "dannyb_kicks", "Y"),
             ("Jordan 4 Retro", 215, 310, "kicksbyjay", "Y"), ("Nike SB Dunk Low", 190, 280, "streetwear_sam", "Y"),
             ("Asics Gel-Kayano 14", 100, 150, "runclub_alex", "Y"), ("Jordan 3 Retro", 180, 255, "solecollector21", "N"),
             ("Nike Air Max 1", 205, 305, "hypehouse_tx", "Y")]
_CARDS = [("Rookie card, graded 9", 70, 120, "cardking88", "N"), ("Team lot, 25 cards", 40, 85, "breakfan_mo", "N"),
          ("Numbered parallel /99", 25, 60, "cardking88", "N"), ("Base set hobby pack", 20, 45, "pullsandbreaks", "N"),
          ("Autograph card", 130, 210, "breakfan_mo", "N")]
ITEMS = ([(D(2026, 8, 9), "Sunday Sneaker Drop", n, "Sneakers", c, p, b, s) for n, c, p, b, s in _SNEAKERS]
         + [(D(2026, 11, 3), "Tuesday Night Breaks", n, "Sports Cards", c, p, b, s) for n, c, p, b, s in _CARDS])
