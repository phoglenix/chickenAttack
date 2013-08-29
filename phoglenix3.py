# A very messy potential field-ish type implementation
# Each turn, makes a grid of shortest distance from each tile to desirable
# tiles (ie. not mine). Each chicken then simply looks at the surrounding 4
# tiles and chooses whichever one has the lowest distance.
# Never moves the last chicken off a tile (unless the tile next to it is not
# mine and has better food in the first half of the game).
# However, checks to see when another friendly chicken has moved into a tile -
# then the last chicken there can be moved.
# Started off quite simple but then tacked on things like preferring areas with
# better food, areas left alone for a long time, areas with fewer chickens (both
# mine and enemy chickens). Things got a bit messy.
# Author: Glen Robertson (phoglenix)

import actions
import heapq
import random

class Player:
    def __init__(self, money_payout_rates, my_spawn_point, their_spawn_point):
        self.money_payout_rates = money_payout_rates
        self.my_spawn_point = my_spawn_point
        self.their_spawn_point = their_spawn_point
        self.width = len(self.money_payout_rates)
        self.height = len(self.money_payout_rates[0])
        # Grid of amount of time each tile has been left unoccupied
        self.unoccupied_time = [ [0] * self.height for i in range(self.width) ]
        # Turn number
        self.turn_no = 0
        # Just the movement actions (ie ignore "STAY")
        self.MOVE_ACTIONS = actions.ALL_ACTIONS[1:]
    
    # Convenience method to check if a position is on the grid
    def in_bounds(self, x, y):
        if not 0 <= x < self.width:
            return False
        if not 0 <= y < self.height:
            return False
        return True
    
    # Convenience method to get the food at a position
    def get_food(self, x, y):
        return 1.0 - self.money_payout_rates[x][y]
    
    # Convenience method to check ownership at a position
    def is_mine(self, x, y, guys):
        return guys[x][y] and guys[x][y][1]
    
    # Remove one of my guys from x,y and add the guy to x2,y2
    # For recording the effect of an order
    # Will error if no guys were at x,y or enemy guys were at x,y
    def update_guys(self, x, y, x2, y2, guys):
        assert guys[x][y]
        num_guys, is_mine = guys[x][y]
        assert is_mine
        assert num_guys > 0
        # Remove from source
        num_guys -= 1
        if num_guys == 0:
            guys[x][y] = None
        else:
            guys[x][y] = (num_guys, is_mine)
        # Add to dest
        if guys[x2][y2]:
            num_guys, is_mine = guys[x2][y2]
            if is_mine:
                num_guys += 1
            else:
                num_guys -= 1
                if num_guys == 0:
                    guys[x2][y2] = None
                    return
        else:
            num_guys, is_mine = 1, True
        guys[x2][y2] = (num_guys, is_mine)
    
    # Find the best action for one chicken at x,y, given grid of current guys,
    # grid of distances to desirable tiles, and whether this is the first
    # chicken on the tile (which has to stay unless there's a vacant better-food
    # spot neighbouring)
    def get_order(self, x, y, guys, dist_to_unowned, first):
        best_action = None
        best_dist = 999
        best_food = 0.0
        for action in self.MOVE_ACTIONS:
            x2, y2 = actions.next_pos( (x,y), action)
            if not self.in_bounds(x2, y2):
                continue
            dist = dist_to_unowned[x2][y2]
            # First ignores distance, only interested in food and unowned tiles
            if first:
                if self.is_mine(x2, y2, guys):
                    dist = 999
                else:
                    dist = 0
            food = self.get_food(x2, y2)
            if dist < best_dist or (dist == best_dist and food > best_food):
                best_action = action
                best_dist = dist
                best_food = food
        
        x2, y2 = actions.next_pos( (x,y), best_action) # New pos
        if first:
            # First guy can't move if it's to a worse food spot...
            # or my guys are there already
            # or we're near the end of the game
            if self.get_food(x2, y2) <= self.get_food(x, y) \
               or self.is_mine(x2, y2, guys) \
               or self.turn_no > 500:
                return ((x, y), actions.STAY)
        
        # Make pos less attractive so others spread out (occasionally)
        if random.random() > 0.9:
            dist_to_unowned[x2][y2] += 0.1
        # Update guys
        self.update_guys(x, y, x2, y2, guys)
        # Give the order
        return ((x, y), best_action)
    
    # Gets called each turn and where you decide where your chickens will go
    def take_turn(self, guys, my_food, their_food, my_money, their_money):
        # Update turn number
        self.turn_no += 1
        
        # Update unoccupied_time: bias movement toward open spaces
        for x in range(self.width):
            for y in range(self.height):
                if guys[x][y]:
                    self.unoccupied_time[x][y] = 0
                else:
                    self.unoccupied_time[x][y] += 1
                    
        
        # Make a grid of distance to closest non-owned tile
        # This got twisted into becoming a general attractiveness measure
        dist_to_unowned = [ [999] * self.height for i in range(self.width) ]
        open = [] # open list of seeds to grow a distance/attractiveness grid
        for x in range(self.width):
            for y in range(self.height):
                # Longer unowned and higher food tiles are more attractive.
                # Magic numbers seemed to help so it wouldn't be overwhelmed by
                # attraction to unoccupied area
                attractiveness = self.unoccupied_time[x][y] * (1 + self.get_food(x,y)) * 0.1
                # Only add non-owned tiles
                if not self.is_mine(x, y, guys):
                    # Attraction is represented as negative distance
                    open.append( (-attractiveness, x, y) )
        
        for d, x, y in open:
            dist_to_unowned[x][y] = d
        # Djikstra's algorithm to fill out grid of shortest distances
        heapq.heapify(open)
        while len(open) > 0:
            d, x, y = heapq.heappop(open)
            if dist_to_unowned[x][y] < d:
                continue # Shorter dist found already
            for m in self.MOVE_ACTIONS:
                x2, y2 = actions.next_pos( (x,y), m)
                if not self.in_bounds(x2, y2):
                    continue
                # Bias around enemy guys
                # and places there are lots of my guys already
                cost = 1
                if guys[x2][y2]:
                    num_guys, is_mine = guys[x2][y2]
                    if is_mine:
                        cost = 1 + 0.1*num_guys
                    else:
                        cost = num_guys
                if dist_to_unowned[x2][y2] > d + cost:
                    dist_to_unowned[x2][y2] = d + cost
                    heapq.heappush(open, (d + cost, x2, y2))
        
        # Make a list of all my guys, sorted by most to least food
        # Sorting was originally to help guys move toward higher food but I
        # don't think it's actually necessary any more.
        all_guys = []
        for x in range(self.width):
            for y in range(self.height):
                if not self.is_mine(x, y, guys): continue
                num_guys, is_mine = guys[x][y]
                all_guys.append( (self.get_food(x,y), x, y, num_guys) )
        all_guys.sort(reverse=True)
        
        # Get the best order for each guy. Record where guys still can move
        # (max of 1 guy still can move in each square as only the first guy
        # might choose to STAY)
        orders = {}
        still_can_move = {}
        for unused, x, y, num_guys in all_guys:
            for i in range(num_guys):
                # Get the best order for this guy
                position, action = self.get_order(x, y, guys, dist_to_unowned, i == 0)
                
                if action == actions.STAY:
                    still_can_move[position] = True
                else:
                    order = (position, action)
                    if order not in orders:
                        orders[order] = 1
                    else:
                        orders[order] += 1
        # Try moving the guys that still_can_move if other guys have moved into their square
        # Iterate over orders looking to see if destination square still can move
        open = orders.keys()
        while len(open) > 0:
            # Order stores origin position, translate to destination position
            origin, action = open.pop()
            position = actions.next_pos(origin, action)
            if position in still_can_move:
                still_can_move.pop(position)
                x, y = position
                position, action = self.get_order(x, y, guys, dist_to_unowned, False)
                # Action can never be STAY because this is not being treated as the first guy
                # on the square any more (because someone else is taking its space as first)
                order = (position, action)
                if order not in orders:
                    orders[order] = 1
                else:
                    orders[order] += 1
                open.append(order)
        
        return orders
