import os
import glob
import sys
import warnings
import itertools
import metquest as mq
from metquest import find_transport_rxns

warnings.filterwarnings("ignore")


def find_relievedrxns(model, org_info, org_info_pert):
    relieved = {}
    detailed_rel_rxns = {}
    rel_rxns_name = {}
    for i in org_info_pert:
        relieved[i] = list(set(org_info_pert[i]) - set(org_info[i]))

    for i in model:
        j = i.id
        detailed_rel_rxns[j] = []
        rel_rxns_name[j] = []
        if len(relieved[j]):
            rxn_ids = []
            for r in i.reactions:
                rxn_ids.append(r.id)
            for rel in relieved[j]:
                rel_rxn = i.reactions[rxn_ids.index(rel)].reaction
                detailed_rel_rxns[j].append(rel_rxn)
                rel_rxns_name[j].append(i.reactions[rxn_ids.index(rel)].name)

    return relieved, detailed_rel_rxns, rel_rxns_name


def find_stuck_rxns(model, community, seedmet_file, no_of_orgs):
    # Constructing graphs

    warnings.filterwarnings("ignore")
    G, full_name_map = mq.construct_graph.create_graph(community, no_of_orgs)
    if not os.path.exists('results'):
        os.makedirs('results')
    f = open(seedmet_file, 'r')

    # Reading seed metabolites

    seedmets, temp_seedmets = [], []
    while True:
        l = f.readline().strip()
        if l == '': break
        temp_seedmets.append(l)
    f.close()

    for m in model:
        for i in temp_seedmets:
            seedmets.append(m.id + ' ' + i)
    seedmets = set(seedmets)

    all_possible_combis = list(itertools.combinations(list(range(len(community))), int(no_of_orgs)))
    if no_of_orgs > 1 and sorted(community)[0][0] == '0':
        all_possible_combis = all_possible_combis[:len(community) - 1]
    org_info = {}
    scope = {}
    print('No. of graphs constructed: ', len(G))

    # This loop finds all the stuck reaction

    for i in range(len(all_possible_combis)):
        lbm, sd, s = mq.guided_bfs.forward_pass(G[i], seedmets)
        for j in range(len(all_possible_combis[i])):
            stuck = []
            rxnNode = []
            model1 = community[all_possible_combis[i][j]].replace('.xml', '')
            visited = list(sd.keys())
            for r in G[i].nodes:
                if r.find(model1) >= 0:
                    rxnNode.append(r)
            for rxn in rxnNode:
                if rxn in visited:
                    continue
                elif rxn.find('ERR') >= 0:
                    continue
                elif rxn.find('Org') >= 0:
                    if (rxn[len(model1) + 5] == 'I') or (rxn[len(model1) + 5] == 'R'):
                        stuck.append(rxn)
            org_info[model1] = stuck
            scope[model1] = s
    return org_info, scope, full_name_map


def decrypt_org_info(org_info, namemap):
    """
    This function decrypts the rxn ids using the data in corresponding namemaps
    :param org_info:
    :param namemap:
    :return:
        org_info: An dictionary of decrypted rxn ids for each community
    """
    for i in org_info:
        for j in range(len(org_info[i])):
            org_info[i][j] = namemap[org_info[i][j]]
    return org_info


def calculate_higherorderMSI(path, sd_file, cluster_file):
    os.chdir(path)
    file_names = glob.glob('*.xml')
    if not file_names:
        file_names = glob.glob('*.sbml')

    if not file_names:
        print("There are no .xml files. Please check the path")
    print("Filenames", file_names)
    sys.path.append(path)
    community = file_names
    community.sort()
    transport_rxns, model = find_transport_rxns(community)
    org_info, scope, namemap = find_stuck_rxns(model, community, sd_file, len(community))
    org_info = decrypt_org_info(org_info, namemap)
    org_info_wo_trans_rxn = {}
    for i in org_info:
        org_info_wo_trans_rxn[i] = list(set(org_info[i]) - set(transport_rxns))

    if not os.path.exists('results/clusterKO_' + os.path.basename(cluster_file).replace('.txt', '') +
                          '_' + os.path.basename(sd_file).replace('.txt', '') + '/data_analysis'):
        os.makedirs('results/clusterKO_' + os.path.basename(cluster_file).replace('.txt', '') + '_' +
                    os.path.basename(sd_file).replace('.txt', '') + '/data_analysis')
    f = open('results/clusterKO_' + os.path.basename(cluster_file).replace('.txt', '') + '_' +
             os.path.basename(sd_file).replace('.txt', '') + '/communityALL.csv', 'w')
    for i in org_info_wo_trans_rxn:
        f.write(i + ',' + str(len(org_info_wo_trans_rxn[i])) + '\n')
    f.close()

    if cluster_file == 'individual_clusters':
        file_names = glob.glob('*.xml')
        if not file_names:
            file_names = glob.glob('*.sbml')
        rem_org_list1 = []
        rem_org_list2 = []
        for i in file_names:
            rem_org_list1.append([i])
            rem_org_list2.append([i])
        for nclus in range(len(rem_org_list2)):
            for i in range(len(rem_org_list2[nclus])):
                rem_org_list2[nclus][i] = rem_org_list2[nclus][i].replace('.xml', '')
    else:
        f = open(cluster_file, 'r')
        temp = f.read()
        f.close()
        l = temp.split("\"i\"")
        l.pop(0)
        rem_org_list1 = []
        rem_org_list2 = []
        for ncluster in range(len(l)):
            rem_org_list1.append([])
            rem_org_list2.append([])
            temp_list = l[ncluster].split('\n')
            for i in range(1, len(temp_list) - 1):
                rem_org_list1[ncluster].append(temp_list[i].split(' ')[0].replace('\"', ''))
                rem_org_list2[ncluster].append(temp_list[i].split(' ')[0].replace('\"', ''))
    for nclus in range(len(rem_org_list2)):
        for i in range(len(rem_org_list2[nclus])):
            rem_org_list2[nclus][i] = rem_org_list2[nclus][i].replace('.xml', '')

    f = open('results/clusterKO_' + os.path.basename(cluster_file).replace('.txt', '') + '_' +
             os.path.basename(sd_file).replace('.txt', '') + '/higher_order_msi.csv', 'w')
    for n in range(len(rem_org_list1)):
        #for n in [1]:
        os.chdir(path)
        new_models = model.copy()
        new_community = glob.glob('*.xml')
        if not new_community:
            new_community = glob.glob('*.sbml')
        new_community.sort()
        for i in rem_org_list1[n]:
            if i in new_community:
                new_models.remove(new_models[new_community.index(i)])
                new_community.remove(i)
        org_info_pert, scope_pert, namemap_pert = \
            find_stuck_rxns(model, new_community, sd_file, len(new_community))
        org_info_pert = decrypt_org_info(org_info_pert, namemap_pert)
        org_info_pert_wo_trans_rxn = {}
        for i in org_info_pert:
            org_info_pert_wo_trans_rxn[i] = list(set(org_info_pert[i]) - set(transport_rxns))

        g = open('results/clusterKO_' + os.path.basename(cluster_file).replace('.txt', '') + '_' +
                 os.path.basename(sd_file).replace('.txt', '') + '/community_without_C' + str(n) + '.csv', 'w')
        for m in org_info_pert_wo_trans_rxn:
            g.write(m + ',' + str(len(org_info_pert_wo_trans_rxn[m])) + '\n')
        g.close()
        stuck_com = 0
        stuck_new_com = 0
        for i in org_info_wo_trans_rxn:
            if i not in rem_org_list2[n]:
                stuck_com += len(org_info_wo_trans_rxn[i])
        for i in org_info_pert_wo_trans_rxn:
            stuck_new_com += len(org_info_pert_wo_trans_rxn[i])
        msi = 1 - (stuck_com / stuck_new_com)
        for i in rem_org_list2[n]:
            f.write('all,C_' + str(n) + '#' + i + ',' + str(msi) + '\n')
        print(n, 'th cluster')

        if msi:
            relieved, detailed_rel_rxns, rel_rxns_name = find_relievedrxns(new_models, org_info,
                                                                           org_info_pert)
            g = open('results/clusterKO_' + os.path.basename(cluster_file).replace('.txt', '')
                     + '_' + os.path.basename(sd_file).replace('.txt', '') +
                     '/data_analysis/relieved_rxns_' + str(n) + '.tsv', 'w')
            g.write('acceptor\trelieved reactions\n')

            for i in relieved:
                g.write(i + '\t')
                rel_rxns = list(set(relieved[i]))
                det_rel_rxns = list(set(detailed_rel_rxns[i]))
                rel_rxn_nam = list(set(rel_rxns_name[i]))
                for j in rel_rxns:
                    g.write(j + '\t')
                g.write('\n')
                g.write('\t')
                for d in rel_rxn_nam:
                    g.write(d + '\t')
                g.write('\n')
                g.write('\t')
                for k in det_rel_rxns:
                    g.write(k + '\t')
                g.write('\n')
            g.close()

            with open('results/clusterKO_' + os.path.basename(cluster_file).replace('.txt', '') + '_' +
                      os.path.basename(sd_file).replace('.txt', '') +
                      '/data_analysis/clus' + str(n) + '.csv', 'w') as h:
                h.write('clus' + str(n) + '\n')
                for i in rem_org_list2[n]:
                    h.write(i + '\n')
                h.write('num of rxns relieved in the below orgs in the presence of clust' + str(n) + '\n')
                h.write(
                    'org,unpert,clust_' + str(
                        n) + 'KO,rxns relieved,cluster it belongs to,tot num of orgs in that cluster\n')
                Nrelieved = {}
                for i in org_info_pert_wo_trans_rxn:
                    Nrelieved[i] = len(org_info_pert_wo_trans_rxn[i]) - len(org_info_wo_trans_rxn[i])
                    if Nrelieved[i]:
                        h.write(i + ',' + str(len(org_info_wo_trans_rxn[i])) + ',' + str(
                            len(org_info_pert_wo_trans_rxn[i])) + ',' + str(Nrelieved[i]) + ',')
                        for nclus in range(len(rem_org_list2)):
                            if i in rem_org_list2[nclus]:
                                h.write(str(nclus) + ',' + str(len(rem_org_list2[nclus])) + '\n')
                print('clus' + str(n))
    f.close()