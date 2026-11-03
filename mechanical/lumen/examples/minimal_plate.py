# E4 minimal check: 100 x 100 rounded plate, thickness parametric.
#   agentcad run examples/minimal_plate.py --label plate_t6
#   agentcad run examples/minimal_plate.py --label plate_t10 --params T=10
# (agentcad pre-injects build123d + show_object, so no imports are required)
L = 100.0
W = 100.0
R = 8.0
T = 6.0

plate = extrude(RectangleRounded(L, W, R), amount=T)

show_object(plate, id="plate", name="rounded plate",
            options={"color": "#EFEDE6", "expect_solids": 1})
