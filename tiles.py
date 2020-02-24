import matplotlib.pyplot as plt
import tilemapbase
# https://github.com/MatthewDaws/TileMapBase

tilemapbase.init(create=True)
t = tilemapbase.tiles.build_OSM()
my_office = (-16.515999, 28.390851)

degree_range = 0.01
extent = tilemapbase.Extent.from_lonlat(my_office[0] - degree_range, my_office[0] + degree_range,
                                        my_office[1] - degree_range, my_office[1] + degree_range)
extent = extent.to_aspect(1.0)

fig, ax = plt.subplots(figsize=(8, 8), dpi=100)
ax.xaxis.set_visible(False)
ax.yaxis.set_visible(False)

plotter = tilemapbase.Plotter(extent, t, width=1000)
plotter.plot(ax, t)
plt.show()
