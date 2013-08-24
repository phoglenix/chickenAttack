# A very messy potential field-ish type implementation
# Author: Glen Robertson (phoglenix)

import actions
import heapq
import random

class Player:

    #Get passed all the board information that never changes throughout the game.
    #It is recommended that you store these in member variables since you will probably need to look at them later.
    # PARAMS:

    #  money_payout_rates:
    #   This is a 50x50 2D array of floats between 0.0 and 1.0 that tell your bot how money per turn this spot produces
    #   Food production is the inverse of money production and follow the formula food_payout_rate = 1.0 - money_payout_rate
    #   This means areas that produce a lot of money, produce less food

    #  my_spawn_point:
    #   An (x, y) tuple of where your new chickens will hatch each turn

    #  their_spawn_point:
    #   An (x, y) tuple of where your opponent's chickens will hatch each turn
    def __init__(self, money_payout_rates, my_spawn_point, their_spawn_point):
        self.money_payout_rates = money_payout_rates
        self.my_spawn_point = my_spawn_point
        self.their_spawn_point = their_spawn_point
        self.width = len(self.money_payout_rates)
        self.height = len(self.money_payout_rates[0])
        self.unoccupied_time = [ [0] * self.height for i in range(self.width) ]
        self.turn_no = 0

    def in_bounds(self, x, y):
        if not 0 <= x < self.width: # bounds
            return False
        if not 0 <= y < self.height: # bounds
            return False
        return True
    
    def get_food(self, x, y):
        return 1.0 - self.money_payout_rates[x][y]
    
    def is_mine(self, x, y, guys):
        return guys[x][y] and guys[x][y][1]
    
    # Remove the guy from x,y and add the guy to x2,y2
    def update_guys(self,x,y,x2,y2,guys):
        # Remove from source
        guys[x][y] = (guys[x][y][0]-1, True)
        if guys[x][y][0] == 0:
            guys[x][y] = None
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
            guys[x2][y2] = (num_guys, is_mine)
        else:
            guys[x2][y2] = (1, True)
            
    # Gets called each turn and where you decide where your chickens will go
    # PARAMS:

    #   guys:
    #       A 50x50 2D matrix showing where all the guys are on the board.
    #       An entry of 'None' indicates an unoccupied spot.
    #       A space with chickens will be an object with "num_guys" and "is_mine" properties.
    #

    #   my_food:
    #       A float showing how much food you have left over from last turn.

    #   their_food:
    #       A float showing how much food your opponent has left over from last run.

    #   my_money:
    #       A float showing how much money you will earn at market so far

    #   their_money:
    #       A float showing how much money your opponent will earn at market so far

    # RETURN:
    #   a python dict that takes a tuple ((x_pos, y_pos), direction) as a key and the number of guys to move as the value.
    #   direction is defined in action.py

    def take_turn(self, guys, my_food, their_food, my_money, their_money):
        self.turn_no += 1
        width = len(guys)
        height = len(guys[0])
        MOVE_ACTIONS = actions.ALL_ACTIONS[1:]
        
        ### update self.unoccupied_time: bias movement toward open spaces
        for x in range(width):
            for y in range(height):
                if guys[x][y]:
                    self.unoccupied_time[x][y] = 0
                else:
                    self.unoccupied_time[x][y] += 1
                    
        
        ### Make a "map" of distance to closest non-owned square
        dist_to_unowned = [ [999] * height for i in range(width) ]
        open = [] # open list
        for x in range(width):
            for y in range(height):
                attractiveness = self.unoccupied_time[x][y] * (1 + self.get_food(x,y)) * 0.1
                if not guys[x][y]:
                    open.append( (-attractiveness,x,y) )
                else:
                    num_guys, is_mine = guys[x][y]
                    if not is_mine:
                        open.append( (-attractiveness,x,y) )
        
        for d, x, y in open:
            dist_to_unowned[x][y] = d
        # Djikstra to fill out map
        heapq.heapify(open)
        while len(open) > 0:
            d, x, y = heapq.heappop(open)
            if dist_to_unowned[x][y] < d:
                continue # Better dist found already
            for m in MOVE_ACTIONS:
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
        # for y in range(height):
            # for x in range(width):
                # print dist_to_unowned[x][y],
            # print ''
        
        

        orders = {}
        all_guys = [] # in order of best food, most food at start
        for x in range(width):
            for y in range(height):
                if not guys[x][y]: continue

                num_guys, is_mine = guys[x][y]
                if not is_mine: continue
                
                all_guys.append( (self.get_food(x,y), x, y, num_guys) )
        all_guys.sort(reverse=True)
        
        for food, x, y, num_guys in all_guys:
            # Move guys
            for i in range(num_guys):
                action = None
                best_dist = 999
                best_food = 0.0
                for m in MOVE_ACTIONS:
                    x2, y2 = actions.next_pos( (x,y), m)
                    if not self.in_bounds(x2, y2):
                        continue
                    dist = dist_to_unowned[x2][y2]
                    if i == 0: # First guy ignores distance, only interested in food and unowned tiles
                        if self.is_mine(x2, y2, guys):
                            dist = 999
                        else:
                            dist = 0
                    food = self.get_food(x2,y2)
                    if dist < best_dist or (dist == best_dist and food > best_food):
                        action = m
                        best_dist = dist
                        best_food = food
                
                x2, y2 = actions.next_pos( (x,y), action) # New pos
                if i == 0:
                    # First guy can only move if it's to a better food spot...
                    if self.get_food(x2,y2) <= self.get_food(x,y):
                        continue
                    # and my guys aren't there already
                    if self.is_mine(x2,y2,guys):
                        continue
                    # and we're not near the end of the game
                    if self.turn_no > 750:
                        continue
                # Make pos less attractive so others spread out (occasionally)
                if random.random() > 0.9:
                    dist_to_unowned[x2][y2] += 0.1
                
                # Give the order
                key = ((x, y), action)
                if key not in orders:
                    orders[key] = 1
                else:
                    orders[key] += 1
                # Update guys
                self.update_guys(x,y,x2,y2,guys)
                        
        return orders
