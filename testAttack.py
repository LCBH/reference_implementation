#!/usr/bin/env python3
__copyright__ = """
	Copyright 2020 EPFL

	Licensed under the Apache License, Version 2.0 (the "License");
	you may not use this file except in compliance with the License.
	You may obtain a copy of the License at

		http://www.apache.org/licenses/LICENSE-2.0

	Unless required by applicable law or agreed to in writing, software
	distributed under the License is distributed on an "AS IS" BASIS,
	WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
	See the License for the specific language governing permissions and
	limitations under the License.

"""
__license__ = "Apache 2.0"

import time
from datetime import datetime, timedelta

import LowCostDP3T

INF_DAYS = 3 # Infectious days before the positive test (can be changed arbitrarily)
SHIFT_ALICE = 60*2.2 # Shift of the Alice's clock (ahead) in seconds (also, this could be smaller)

global epotimeIsidor            # Isidor's internal clock
global epotimeAlice             # Alice's internal clock
global countDays                # Number of days, using Isidor's clock
# Mock time starts midnight on April 01. We assume Alice's clock is 1 second ahead of Isidor's clock.
epotimeIsidor = datetime.timestamp(
    datetime.strptime("2020-04-01", "%Y-%m-%d")) + 2*60*60 + 1
epotimeAlice = epotimeIsidor - SHIFT_ALICE
countDays = 0


# globally progress all agents' clock
def progressTime(minutes=(24*60)):
    global epotimeIsidor
    global epotimeAlice
    global countDays
    deltaSecs = minutes*60
    for i in range(0, ((datetime.utcfromtimestamp(epotimeIsidor+deltaSecs)) - datetime.utcfromtimestamp(epotimeIsidor)).days):
        print("   + New day for Isidor")
        isidor.next_epoch()
        isidor.next_day()
        countDays += 1
    for i in range(0, ((datetime.utcfromtimestamp(epotimeAlice+deltaSecs)) - datetime.utcfromtimestamp(epotimeAlice)).days):
        print("   + New day for Alice")
        alice.next_epoch()
        alice.next_day()
    epotimeIsidor += deltaSecs
    epotimeAlice += deltaSecs


if __name__ == "__main__":
    # We have three people: Alice, Bob, and Isidor
    alice = LowCostDP3T.MockApp()
    bob = LowCostDP3T.MockApp()
    isidor = LowCostDP3T.MockApp()
    print("Current time: %s." % datetime.utcfromtimestamp(epotimeIsidor))

    # Extreme confinement: no one meets anyone
    for day in range(INF_DAYS+1):
        print("Day %d: Alice, Bob, and Isidor do not have contact. Isidor SK: [%s...]. Current Isidor's date: [%s]." % (
            countDays, isidor.keystore.SKt[0][0:4].hex(), datetime.utcfromtimestamp(epotimeIsidor)))
        progressTime()

    # Yet, Isidor is tested positive
    published_date = infectious_date = datetime.utcfromtimestamp(epotimeIsidor)
    infectious_date = datetime.utcfromtimestamp(
        epotimeIsidor-(INF_DAYS-1)*24*60*60)
    infected_SK = isidor.keystore.SKt[INF_DAYS-1]
    print("\nDay %d: Isidor is tested positive and publish SK_t[day-%s]=[%s...] with infectious time=[%s]. Current SK is [%s...]. So far, not a single entity has received an EphID. Current Isidor's date: [%s]." % (
        countDays, INF_DAYS-1, infected_SK[0:4].hex(), infectious_date, isidor.keystore.SKt[0][0:4].hex(),datetime.utcfromtimestamp(epotimeIsidor)))
    # print("    Isidor would have sent EphID=[%s;...] with SK=[%s;...] at this point." % (test[0],isidor.keystore.SKt[0][0]))

    # So far, not a single entity has received an EphID. In particular, the attacker has not eavesderopped on any.
    # Yet, the attacker can use any published SK (from anynone, Isidor could be anyone) to trigger a false positive in Alice,
    # if he can be close to Alice and if the timing is right.
    fakeTime = epotimeIsidor-2
    print("\n --> Step 1. Attacker fetches Isidor's infected SK_t at time [%s] and compute a valid EphID corresponding to time [%s]." % (
        datetime.utcfromtimestamp(epotimeIsidor), datetime.utcfromtimestamp(fakeTime)))
    lastSK = infected_SK
    for d in range(0, INF_DAYS-2):
        lastSK = LowCostDP3T.KeyStore.get_SKt1(lastSK)
    infected_ephIDs = LowCostDP3T.KeyStore.create_ephIDs(lastSK)
    fakeEphID = infected_ephIDs[-1]
    print("     Fake EphID: [%s...] for SK=[%s...]." %
          (fakeEphID[0:4].hex(), lastSK[0:4].hex()))

    print("\n --> Step 2. Alice's internal clock is 2 minutes ahead of time [%s] and receives the fake EphID multiple times." % (
        datetime.utcfromtimestamp(epotimeAlice)))
    alice.ctmgr.receive_scans(
        [fakeEphID], now=datetime.utcfromtimestamp(epotimeAlice))
    progressTime(2.1)             # after 2 minutes, still receiving the token!
    alice.ctmgr.receive_scans(
        [fakeEphID], now=datetime.utcfromtimestamp(epotimeAlice))

    print("\n --> Step 3. After a while (next day, but it does not really matter), Alice checks if she is at risk. She is not but DP-3T concludes that she is:")
    alice.next_epoch()
    progressTime()
    alice.ctmgr.check_infected(infected_SK, infectious_date.strftime(
        "%Y-%m-%d"), published_date.strftime(
        "%Y-%m-%d"))
