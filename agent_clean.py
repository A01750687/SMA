"""
Simulación de un entorno de limpieza por agentes en una habitación.
Este programa modela una habitación sucia con agentes de limpieza que se mueven para limpiar celdas.
Autores: 
        - Aislinn Ruiz A01750687
        - Miguel Galicia A01750744
Fecha: 08 de noviembre de 2024 
"""

from mesa import Agent, Model
from mesa.time import SimultaneousActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
import random

class CeldaAgent(Agent):
    """
    Agente que representa una celda en la habitación, que puede estar limpia o sucia.
    
    Atributos:
        unique_id (int): Identificador único del agente.
        model (Model): Modelo de simulación al que pertenece el agente.
        sucia (bool): Estado de la celda, True si está sucia, False si está limpia.
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.sucia = False  # Inicializa la celda como limpia

    def limpiar(self):
        """Cambia el estado de la celda a limpia."""
        self.sucia = False


class LimpiadorAgent(Agent):
    """
    Agente que representa un robot limpiador que se mueve por la habitación y limpia celdas sucias.
    
    Atributos:
        unique_id (int): Identificador único del agente.
        model (Model): Modelo de simulación al que pertenece el agente.
        movimientos (int): Contador de los movimientos realizados por el agente.
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.movimientos = 0  # Contador inicializado en cero

    def step(self):
        """
        Realiza un paso de simulación para el agente limpiador.
        Si la celda está sucia, la limpia. Si no, se mueve a una nueva posición.
        """
        celda = self.model.grid.get_cell_list_contents([self.pos])
        
        # Si la celda contiene una instancia de CeldaAgent sucia, procede a limpiarla
        if any(isinstance(obj, CeldaAgent) and obj.sucia for obj in celda):
            for obj in celda:
                if isinstance(obj, CeldaAgent) and obj.sucia:
                    obj.limpiar()
        else:
            # Si la celda está limpia, el agente intenta moverse
            self.mover()

    def mover(self):
        """
        Cambia la posición del agente limpiador a una celda adyacente sin otro limpiador.
        Incrementa el contador de movimientos en cada movimiento realizado.
        """
        posibles_movimientos = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
        
        # Filtra movimientos válidos donde no haya otro agente limpiador
        valid_moves = [
            pos for pos in posibles_movimientos
            if not any(isinstance(a, LimpiadorAgent) for a in self.model.grid.get_cell_list_contents([pos]))
        ]

        # Realiza un movimiento a una posición aleatoria dentro de las válidas
        if valid_moves:
            nueva_posicion = self.random.choice(valid_moves)
            self.model.grid.move_agent(self, nueva_posicion)
            self.movimientos += 1  # Incrementa el contador de movimientos


class HabitacionModel(Model):
    """
    Modelo de la habitación que contiene celdas que pueden estar sucias y agentes limpiadores.
    
    Atributos:
        M (int): Cantidad de filas en la habitación.
        N (int): Cantidad de columnas en la habitación.
        num_agentes (int): Número de agentes limpiadores en el modelo.
        celdas_sucias (int): Número inicial de celdas sucias en la habitación.
        schedule (SimultaneousActivation): Controlador de activación de agentes.
        grid (MultiGrid): Espacio de la habitación donde se colocan los agentes.
        running (bool): Controla si la simulación está activa.
    """
    def __init__(self, M, N, num_agentes, celdas_sucias):
        self.M = M
        self.N = N
        self.num_agentes = num_agentes
        self.celdas_sucias = celdas_sucias
        self.schedule = SimultaneousActivation(self)
        self.grid = MultiGrid(M, N, torus=False)
        self.running = True

        # Inicializa celdas con algunas sucias al azar
        unique_id = 0
        total_celdas = M * N
        posiciones_sucias = self.random.sample(range(total_celdas), celdas_sucias)
        self.dirty_positions = set()

        for i in range(M):
            for j in range(N):
                celda = CeldaAgent(unique_id, self)
                if unique_id in posiciones_sucias:
                    celda.sucia = True
                    self.dirty_positions.add((i, j))
                self.grid.place_agent(celda, (i, j))
                unique_id += 1

        # Agrega los agentes limpiadores en la habitación
        for i in range(num_agentes):
            limpiador = LimpiadorAgent(i, self)
            self.grid.place_agent(limpiador, (1, 1))
            self.schedule.add(limpiador)
            unique_id += 1

        # Configura el recolector de datos
        self.datacollector = DataCollector(
            model_reporters={
                "Celdas Limpias": self.contar_celdas_limpias,
                "Movimientos Totales": self.contar_movimientos
            }
        )

    def contar_celdas_limpias(self):
        """
        Calcula el porcentaje de celdas limpias en la habitación.
        
        Retorna:
            float: Porcentaje de celdas limpias respecto a las celdas iniciales sucias.
        """
        celdas_limpias = sum(
            1 for pos in self.dirty_positions
            for content in self.grid.get_cell_list_contents([pos])
            if isinstance(content, CeldaAgent) and not content.sucia
        )
        porcentaje = (celdas_limpias / self.celdas_sucias) * 100
        return porcentaje

    def contar_movimientos(self):
        """
        Calcula el total de movimientos realizados por los agentes limpiadores.
        
        Retorna:
            int: Suma de los movimientos de todos los agentes limpiadores.
        """
        return sum(agente.movimientos for agente in self.schedule.agents if isinstance(agente, LimpiadorAgent))

    def step(self):
        """
        Realiza un paso de simulación, recolecta datos y evalúa si todas las celdas están limpias.
        Si todas las celdas sucias están limpias, detiene la simulación.
        """
        self.datacollector.collect(self)
        porcentaje_limpias = self.contar_celdas_limpias()
        print(f"Paso {self.schedule.steps}: {porcentaje_limpias:.2f}% de celdas limpias")
        
        if porcentaje_limpias >= 100:
            self.running = False
        else:
            self.schedule.step()


def agent_portrayal(agent):
    """
    Define la representación visual de los agentes en la interfaz de simulación.
    
    Parámetros:
        agent (Agent): Instancia del agente a representar.
        
    Retorna:
        dict: Propiedades visuales del agente en la interfaz.
    """
    if isinstance(agent, LimpiadorAgent):
        return {
            "Shape": "circle",
            "Filled": "true",
            "Layer": 1,
            "Color": "blue",
            "r": 0.5
        }
    elif isinstance(agent, CeldaAgent):
        color = "red" if agent.sucia else "white"
        return {
            "Shape": "rect",
            "Filled": "true",
            "Layer": 0,
            "Color": color,
            "w": 1,
            "h": 1
        }

# Parámetros iniciales de la simulación
M = 10  
N = 10  
num_agentes = 12
celdas_sucias = 36  

# Configuración del servidor de visualización para lanzar la simulación
grid = CanvasGrid(agent_portrayal, M, N, 500, 500)
server = ModularServer(
    HabitacionModel,
    [grid],
    "Simulación de Habitacion y Agentes Limpiadores",
    {
        "M": M,
        "N": N,
        "num_agentes": num_agentes,
        "celdas_sucias": celdas_sucias,
    }
)

server.launch()
