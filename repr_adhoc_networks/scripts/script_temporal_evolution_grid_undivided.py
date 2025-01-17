# coding: utf-8

#============================ IMPORTS ======================================
import numpy as np
import pandas as pd
import networkx as nx
import os
from tqdm import tqdm
from swarm_sim import *


#========================== GLOBAL VARIABLES ==============================
PATH = 'data\\v5-grid-7x7-sats-scenario\\coords_v1_if_LLO-'
EXPORT_PATH = 'output\\data'
ROW_DATA = 7


CONNECTION_RANGE = 30 # km
GRID_SIZE = 7 # 7x7=49 satellites
NB_NODES = GRID_SIZE*GRID_SIZE
DURATION = 8641 # Number of data rows, not time!
REVOLUTION = 1800 # Number of data rows
SAMPLE_STEP = 12 # Take one out of 12 samples (alleviates calculations)


#============================= FUNCTIONS ==================================
def add_data_row(data_dict,tsp,con,red,disp,mod,crit,cost,eff):
        data_dict['Timestamp'].append(tsp)
        data_dict['Flow robustness'].append(con)
        data_dict['Redundancy_avg'].append(red)
        data_dict['Disparity_avg'].append(disp)
        data_dict['Modularity'].append(mod)
        data_dict['Criticity'].append(crit)
        data_dict['RCost'].append(cost)
        data_dict['Efficiency'].append(eff)
    

def swarm_betweeness_centrality(graph):
    bc = nx.betweenness_centrality(graph)
    bc_dict = {
        'Node':list(bc.keys()),
        'BC':list(bc.values())
    }
    return bc_dict


def kronecker_delta(ni, nj):
    if ni.group==nj.group:
        return 1
    return 0


def modularity(graph):
    nb_edges = nx.number_of_edges(graph)
    element = 0
    for ni in graph.nodes:
        for nj in graph.nodes:
            adj = 0
            delta = 1 # Same group for everyone
            if graph.has_edge(ni,nj):
                adj = 1
            element += (adj - nx.degree(graph,ni)*nx.degree(graph,nj)/(2*nb_edges)) * delta
    modularity = element / (2*nb_edges)
    return modularity


def origin_destination_pairs():
    return NB_NODES*(NB_NODES-1)/2


def pair_disparity(shortest_paths:list, spl:int):
    if len(shortest_paths)==1:
        return 0.0
    path_graphs = {}
    for i,path in enumerate(shortest_paths):
        path_graphs[i] = nx.path_graph(path)
    disparity = 0
    pairs = []
    for idx1,p1 in path_graphs.items():
        for idx2,p2 in path_graphs.items():
            if idx1 != idx2 and set([idx1,idx2]) not in pairs:
                pairs.append(set([idx1,idx2]))
                its = nx.intersection(p1,p2)
                disp = 1 - nx.number_of_edges(its)/spl
                disparity += disp
    return disparity/len(pairs)



#============================ INITIALIZE TOPOLOGY ==============================

satellites = {} # Dict(sat_id: DataFrame)
with tqdm(total=NB_NODES, desc='Extracting GRID data') as pbar:
    sat_idx = 0
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            df_data = pd.read_csv(PATH+str(i)+'-'+str(j)+'.csv', skiprows= lambda x: x<ROW_DATA, header=0)
            satellites[sat_idx] = df_data
            sat_idx += 1
            pbar.update(1)
        
swarm_data = {} # Dict{timestamp: Swarm}
with tqdm(total=REVOLUTION, desc='Converting to topologies') as pbar:
    for t in range(REVOLUTION):
        swarm_data[t] = Swarm(connection_range=30,
                    nodes = [Node(id, sat['xF[km]'].iloc[t], sat['yF[km]'].iloc[t], sat['zF[km]'].iloc[t]) for id,sat in satellites.items()]
                    )
        pbar.update(1)

neighbor_matrices = {} # Dict{timestamp: matrix}
with tqdm(total=REVOLUTION, desc='Computing neighbor matrices') as pbar:
    for t in range(REVOLUTION):
        neighbor_matrices[t] = swarm_data[t].neighbor_matrix()
        pbar.update(1)

topo_graphs = {} # Dict{timestamp: Graph}
with tqdm(total=REVOLUTION, desc='Converting to NetworkX graphs') as pbar:
    for t in range(REVOLUTION):
        topo_graphs[t] = swarm_data[t].swarm_to_nxgraph()
        pbar.update(1)


#==================================== BEGIN =====================================

# Dict to store data (convert later into pd.DataFrame)
final_data = {
    'Timestamp':[],
    'Flow robustness':[],
    'Redundancy_avg':[],
    'Disparity_avg':[],
    'Modularity':[],
    'Criticity':[],
    'RCost': [],
    'Efficiency': []
}

print('\nNo graph division here.\n')


nb_max = origin_destination_pairs()

with tqdm(total=REVOLUTION/SAMPLE_STEP, desc='Temporal evolution') as pbar:
    for t in range(1): #np.arange(0, REVOLUTION, SAMPLE_STEP):
        swarm = swarm_data[t]
        graph = topo_graphs[t]

        visited_pairs, paths = [], []
        redundancies = []
        disparities = []
        total_spl = 0
        pair_efficiency = 0.0

        for src_id in graph.nodes:
            for dst_id in graph.nodes:
                if dst_id != src_id and set((src_id,dst_id)) not in visited_pairs:  
                    visited_pairs.append(set((src_id,dst_id))) 
                    pair_red = 0
                    print('Computing pair efficiency...')
                    pair_efficiency += nx.efficiency(graph, src_id, dst_id)
                    if nx.has_path(graph, src_id, dst_id):
                        paths.append(set((src_id,dst_id))) 
                        print('Computing SPL...')
                        spl = nx.shortest_path_length(graph, source=src_id, target=dst_id)
                        print('Computing all shortest paths...')
                        shortest_paths = list(nx.all_shortest_paths(graph, src_id, dst_id))
                        pair_red += len(shortest_paths)
                        print('Computing pair disparity...')
                        pair_disp = pair_disparity(shortest_paths, spl)
                        total_spl += spl

                        redundancies.append(pair_red)
                        disparities.append(pair_disp)

        flow = len(paths)/nb_max
        mod = modularity(graph)
        df_bc = pd.DataFrame(swarm_betweeness_centrality(graph))
        crit = len(df_bc[df_bc['BC']>=0.05]['BC'])
        cost = total_spl*2
        eff = pair_efficiency/nb_max

        add_data_row(final_data,
                        t,
                        flow,
                        np.mean(redundancies),
                        np.mean(disparities),
                        mod,
                        crit,
                        cost,
                        eff)
        pbar.update(1)
 

#=============================== EXPORTING RESULTS ============================
results_df = pd.DataFrame(final_data)
print(results_df.head())
print(results_df.shape[0], 'rows')

filename = 'grid_temporal_undivided_sampled_'+str(SAMPLE_STEP)+'.csv'
print('\nExporting to', os.path.join(EXPORT_PATH, filename))
results_df.to_csv(os.path.join(EXPORT_PATH, filename), sep=',')