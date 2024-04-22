#!/usr/bin/env python

import asyncio

t_max = 10.0
t_error = 1e-4


class Circuit:
    """This class simulates the given circuit with the time dependant resistance values."""

    voltage = 10.0
    r_dot = 10.0
    dt = 0.1
    r_l = 30.0

    def __init__(
        self,
        voltmeter,
        ammeter,
        ohmmeter,
        ra_ohmmeter,
    ) -> None:
        self.reset()
        self.halt = False

        self.voltmeter = voltmeter
        self.ammeter = ammeter
        self.ohmmeter = ohmmeter
        self.ra_ohmmeter = ra_ohmmeter

    async def counter_t(self) -> None:
        """The core loop in which circuit component values and time stamp is updated: You don't need to use this method in your code in most situations; Use start method instead."""
        while self.t < t_max - t_error:
            while self.halt:
                await asyncio.sleep(self.dt)
            await asyncio.sleep(self.dt)
            self.t += self.dt
            self.r_1 += self.r_dot * self.dt
            self.r_2 -= self.r_dot * self.dt

    async def bootstrap(self) -> None:
        """Bootstraps the circuit assets, such as ammeter, voltmeter, etc. You don't need to use this method in your code in most situations; Use start method instead."""
        # Import tasks to be scheduled corresponding to each present measurement device and the circuit itself
        tasks = [self.counter_t()]

        if self.voltmeter:
            tasks.append(self.voltmeter.counter_v(circuit=self))

        if self.ammeter:
            tasks.append(self.ammeter.counter_c(circuit=self))

        if self.voltmeter and self.ammeter:
            if self.ohmmeter:
                tasks.append(
                    self.ohmmeter.counter_r(
                        voltmeter=self.voltmeter, ammeter=self.ammeter
                    )
                )

            if self.ra_ohmmeter:
                tasks.append(
                    self.ra_ohmmeter.counter_r(
                        voltmeter=self.voltmeter, ammeter=self.ammeter
                    )
                )

        # Schedule coroutines and await them
        await asyncio.gather(*tasks)

    def start(self) -> None:
        """Bootstraps and start the circuit simulation."""
        self.halt = False
        self.timer = self.bootstrap()
        asyncio.run(self.timer)

    def pause(self) -> None:
        """Pauses the simulation."""
        self.halt = True

    def reset(self) -> None:
        """Resets the simulation values and time stamp."""
        self.r_1 = 0.0
        self.r_2 = 100.0
        self.t = 0.0

    def restart(self) -> None:
        """Resets the circuit values and starts the simulation from the begining."""
        self.reset()
        self.start()

    def read_voltage(self) -> float:
        """Computes the voltmeter value based on the current values of the circuit components."""
        r_par = self.r_l * self.r_2 / (self.r_l + self.r_2)
        return r_par * self.voltage / (r_par + self.r_1)

    def read_current(self) -> float:
        """Computes the ammeter value based on the current values of the circuit components."""
        return self.read_voltage() / self.r_l


class Voltmeter:
    """Simulates the voltmeter in the circuit."""

    dt = 0.1

    def __init__(self) -> None:
        self.voltage = 0.0
        self.t = 0.0

    async def counter_v(self, circuit: Circuit) -> None:
        while self.t < t_max - t_error:
            await asyncio.sleep(self.dt)
            self.voltage = circuit.read_voltage()
            self.t = circuit.t
            print(f"time stamp: {round(self.t, 1)} s\tvoltage: {self}")

    def __str__(self) -> str:
        return f"{self.voltage} v"


class Ammeter:
    """Simulates the ammeter in the circuit."""

    dt = 0.3

    def __init__(self) -> None:
        self.current = 0.0
        self.t = 0.0

    async def counter_c(self, circuit: Circuit) -> None:
        while self.t < t_max - t_error:
            await asyncio.sleep(self.dt)
            self.current = circuit.read_current()
            self.t = circuit.t
            print(f"time stamp: {round(self.t, 1)} s\tcurrent: {self}")

    def __str__(self) -> str:
        return f"{self.current} mA"


class Ohmmeter:
    """Simulates the ohmmeter in the circuit."""

    dt = 1.0

    def __init__(self) -> None:
        self.resistance = 0.0
        self.t = 0.0

    async def counter_r(self, voltmeter: Voltmeter, ammeter: Ammeter) -> None:
        while self.t < t_max - t_error:
            await asyncio.sleep(self.dt)
            self.t = max(voltmeter.t, ammeter.t)
            try:
                self.resistance = voltmeter.voltage / ammeter.current
            except ZeroDivisionError:
                continue
            print(f"time stamp: {round(self.t, 1)} s\tresistance: {self}")

    def __str__(self) -> str:
        return f"{self.resistance} kΩ"


class RAOhmmeter(Ohmmeter):
    """Simulates the rolling average ohmmeter in the circuit."""

    t_interval = 2.0

    def __init__(self) -> None:
        self.readings_buffer = {}
        self.resistance = 0.0
        self.t = 0.0

    def rolling_average(self) -> float:
        f"""Takes the rolling average of last {self.t_interval} s-read load resistances"""
        # Determine the outdated reading
        to_be_removed = []
        for timestamp in self.readings_buffer.keys():
            if timestamp + self.t_interval < self.t - t_error:
                to_be_removed.append(timestamp)

        # removes the outdated readings
        for timestamp in to_be_removed:
            del self.readings_buffer[timestamp]

        # Take the average of the remaining readings
        return sum(self.readings_buffer.values()) / len(self.readings_buffer)

    async def counter_r(self, voltmeter: Voltmeter, ammeter: Ammeter) -> None:
        while self.t < t_max - t_error:
            await asyncio.sleep(self.dt)
            self.t = max(voltmeter.t, ammeter.t)
            try:
                self.readings_buffer[self.t] = voltmeter.voltage / ammeter.current
            except ZeroDivisionError:
                continue

            self.resistance = self.rolling_average()
            print(f"time stamp: {round(self.t, 1)} s\tra resistance: {self}")


if __name__ == "__main__":
    # Initialize the circuit assets
    vm = Voltmeter()
    am = Ammeter()
    om = Ohmmeter()
    ra_om = RAOhmmeter()

    # Initialize the circuit simulator with either of the following 5 lines
    circ = Circuit(voltmeter=vm, ammeter=am, ohmmeter=om, ra_ohmmeter=ra_om)
    # circ = Circuit(voltmeter=vm, ammeter=am, ohmmeter=None, ra_ohmmeter=None)
    # circ = Circuit(voltmeter=vm, ammeter=None, ohmmeter=None, ra_ohmmeter=None)
    # circ = Circuit(voltmeter=None, ammeter=am, ohmmeter=None, ra_ohmmeter=None)
    # circ = Circuit(voltmeter=None, ammeter=None, ohmmeter=None, ra_ohmmeter=None)

    # Start the simulation
    circ.start()
