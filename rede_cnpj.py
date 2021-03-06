import random

import numpy as np
import pandas as pd

import networkx as nx
from networkx.readwrite import json_graph

COL_FLOAT64 = ['capital_social']

class RedeCNPJ:
    __conBD = None  
    __nivel_max = 1
    __qualificacoes = 'TODAS'
    
    G = None

    def __init__(self, conBD, nivel_max=1, qualificacoes='TODAS'):
        self.__conBD = conBD
        self.__nivel_max = nivel_max
        self.__qualificacoes = qualificacoes

        self.G = nx.DiGraph()

    def insere_pessoa(self, tipo_pessoa, id_pessoa):
        self._vinculos(tipo_pessoa=tipo_pessoa, id_pessoa=id_pessoa)

    def dataframe_pessoas(self):
        node_data = self.G.nodes(data=True)
        return pd.DataFrame([i[1] for i in node_data], index=[i[0] for i in node_data])

    def dataframe_vinculos(self):
        edge_data = self.G.edges(data=True)
        return pd.DataFrame([i[2] for i in edge_data], 
                            index=pd.MultiIndex.from_tuples([(i[0], i[1]) for i in edge_data], 
                            names=['source','target']))

    def json(self):
        return json_graph.node_link_data(self.G)

    def gera_json(self, path):
        import json

        with open(path, "w") as f:
            f.write(json.dumps(self.json()))

    def gera_graphml(self, path):
        nx.write_graphml(self.G, path)

    def gera_gexf(self, path):
        # Antes de gerar esse formato, necessario adaptar alguns atributos do grafo
        G_adapt = self.G.copy()

        pos = nx.spring_layout(G_adapt, dim=4, scale=1000)
        
        for node in G_adapt.nodes:
            tipo_pessoa = G_adapt.nodes[node]['tipo_pessoa']

            G_adapt.nodes[node]['label'] = G_adapt.nodes[node]['nome']

            # Configura atributos de visualizacao necessarios para alguns leitores
            G_adapt.nodes[node]['viz'] = {'size':10}

            if tipo_pessoa == 1:
                if G_adapt.nodes[node]['situacao'] == '02':
                    G_adapt.nodes[node]['viz']['color'] = {'a':1,'r':1,'g':57,'b':155}
                else:
                    G_adapt.nodes[node]['viz']['color'] = {'a':1,'r':255,'g':0,'b':0}
            else:
                G_adapt.nodes[node]['viz']['color'] = {'a':1,'r':46,'g':125,'b':32}

            G_adapt.nodes[node]['viz']['position'] = {'x':pos[node][0],
                                                      'y':pos[node][1],
                                                      'z':5}

            # Converte cols para float, por incompatibilidade do nx com o numpy.float64
            for coluna in COL_FLOAT64:
                if coluna in G_adapt.nodes[node]:
                    G_adapt.nodes[node][coluna] = float(G_adapt.nodes[node][coluna])

        nx.write_gexf(G_adapt, path)

    def insere_com_cpf_ou_nome(self, cpf='', nome=''):
        # A partir de um nome ou um cpf, busca socios com esses dados e inclui na rede
        sql = '''
            SELECT distinct 
                tipo_socio, 
                cnpj_cpf_socio, 
                nome_socio 
            FROM 
                socios 
        '''
        if cpf != '':
            sql += '''
                WHERE cnpj_cpf_socio = '{0}'
            '''.format(cpf)
            
        else:
            sql += '''
                WHERE nome_socio = '{0}'
            '''.format(nome)
        
        empresas_socios = pd.read_sql_query(sql, self.__conBD)
        if len(empresas_socios) > 0:
            for _, emp_socio in empresas_socios.iterrows():
                cnpj_cpf_socio = emp_socio['cnpj_cpf_socio']
                nome_socio = emp_socio['nome_socio']
                tipo_socio = int(emp_socio['tipo_socio'])

                if tipo_socio == 1:
                    self._vinculos(tipo_pessoa=tipo_socio, id_pessoa=cnpj_cpf_socio)
                if tipo_socio == 2:
                    self._vinculos(tipo_pessoa=tipo_socio, id_pessoa=(cnpj_cpf_socio,nome_socio))
        else:
            print('Nenhum socio encontrado com o cpf ou nome informado.')

    def _vinculos(self, tipo_pessoa, id_pessoa, nivel=0, origem=None):
        nome = None

        # Monta o id do node de acordo com o tipo de pessoa
        if tipo_pessoa == 1:
            id_pessoa_str = id_pessoa
        else:
            nome = id_pessoa[1]
            id_pessoa_str = id_pessoa[0] + nome

        # Nova pessoa
        if id_pessoa_str not in self.G:
            nova_pessoa = True
            self.G.add_node(id_pessoa_str, nome=nome, tipo_pessoa=tipo_pessoa, nivel=nivel)

            #self.G.nodes[id_pessoa_str]['tipo_pessoa'] = tipo_pessoa
            #self.G.nodes[id_pessoa_str]['nivel'] = nivel

            # Se for PJ, pega dados da empresa na tabela de empresas
            if (tipo_pessoa == 1):
                sql = '''
                    SELECT
                        cnpj,
                        matriz_filial, 
                        razao_social, 
                        nome_fantasia, 
                        situacao, 
                        data_situacao,
                        motivo_situacao,
                        nm_cidade_exterior,
                        cod_pais,
                        nome_pais,
                        cod_nat_juridica,
                        data_inicio_ativ, 
                        cnae_fiscal,
                        tipo_logradouro,
                        logradouro,
                        numero,
                        complemento,
                        bairro,
                        cep,
                        uf,
                        cod_municipio,
                        municipio,
                        email,
                        qualif_resp,
                        capital_social,
                        porte,
                        opc_simples,
                        data_opc_simples,
                        data_exc_simples,
                        opc_mei,
                        sit_especial,
                        data_sit_especial
                    FROM
                        empresas
                    WHERE
                        cnpj = '{0}'
                '''.format(id_pessoa)
                
                try:
                    empresa = pd.read_sql_query(sql, self.__conBD).iloc[0,:] # pega primeiro registro

                    # inclui atributos no node, com base nas colunas da tabela de empresas
                    if (str(empresa['nome_fantasia']).strip() == '') or (str(empresa['nome_fantasia']).strip() == 'NAO POSSUI'):
                        self.G.nodes[id_pessoa_str]['nome'] = empresa['razao_social'] 
                    else:
                        self.G.nodes[id_pessoa_str]['nome'] = empresa['nome_fantasia'] 

                    for k, v in empresa.items():
                        self.G.nodes[id_pessoa_str][k] = v

                except:
                    print('Empresa nao encontrada: {}'.format(id_pessoa_str))

            else:
                # Se no for pessoa fisica
                self.G.nodes[id_pessoa_str]['cpf'] = id_pessoa[0]
        else:
            nova_pessoa = False
            nivel_anterior = self.G.nodes[id_pessoa_str]['nivel']

            if nivel < nivel_anterior:
                self.G.nodes[id_pessoa_str]['nivel'] = nivel
        
        # Condicoes para explorar "relacionados":
        # 1) Nivel atual ser menor do que configuracao max_nivel; e
        # 2) Relacionamentos não terem sido totalmente explorados antes, por
        #       a) ser uma pessoa nova OU
        #       b) nao é uma pessoa nova, mas o nivel atual é menor do que o nivel anterior dessa pessoa 
        if (nivel < self.__nivel_max) and (nova_pessoa or nivel < nivel_anterior):   
            # obtem todas as relacoes de sociedades que envolvam esse PJ ou PF

            # Verifica se relacionados ja estao no grafo ou se precisa buscar no BD
            if (not nova_pessoa) and (nivel_anterior < self.__nivel_max):
                # Relacionados ja estao no grafo, nao precisa buscar no BD

                # navega para os socios
                for id_socio_str in self.G.predecessors(id_pessoa_str):
                    node_socio = self.G.nodes[id_socio_str]
                    tipo_socio = node_socio['tipo_pessoa']

                    if tipo_socio == 1:
                        # socio eh PJ
                        socio = id_socio_str
                    else:
                        # socio eh PF
                        socio = (node_socio['cpf'],node_socio['nome'])

                    self._vinculos(tipo_pessoa=tipo_socio, id_pessoa=socio, nivel=nivel+1, origem=id_pessoa)

                # navega para empresas das quais e socio
                for empresa in self.G.successors(id_pessoa_str):
                    self._vinculos(tipo_pessoa=1, id_pessoa=empresa, nivel=nivel+1, origem=id_pessoa)

            else:
                # Relacionados ainda nao estao no grafo. Buscar no BD
                sql = '''
                    SELECT 
                        cnpj, 
                        tipo_socio, 
                        cnpj_cpf_socio, 
                        nome_socio, 
                        cod_qualificacao, 
                        data_entrada 
                    FROM 
                        socios 
                '''
                if tipo_pessoa == 1: # se for PJ, consultar socios e também empresas das quais essa PJ pode ser socia
                    sql += '''
                        WHERE cnpj = '{0}' OR 
                              cnpj_cpf_socio = '{0}'
                    '''.format(id_pessoa)
                    
                else: # se for PF, consultar empresas das quais essa PF pode ser socia
                    sql += '''
                        WHERE cnpj_cpf_socio = '{0}' AND 
                              nome_socio = '{1}'
                    '''.format(id_pessoa[0],id_pessoa[1])
                
                empresas_socios = pd.read_sql_query(sql, self.__conBD)

                # Itera por cada relacionamento encontrado na base
                for _, emp_socio in empresas_socios.iterrows():
                    cod_qualificacao = emp_socio['cod_qualificacao']

                    # Apenas adiciona relacionamento se for qualificacao de interesse
                    if (self.__qualificacoes == 'TODAS') | (cod_qualificacao in self.__qualificacoes): 

                        cnpj = emp_socio['cnpj']
                        cnpj_cpf_socio = emp_socio['cnpj_cpf_socio']
                        nome_socio = emp_socio['nome_socio']
                        tipo_socio = int(emp_socio['tipo_socio'])
                        data_entrada = emp_socio['data_entrada']

                        if tipo_socio == 1:
                            # socio eh PJ
                            socio = cnpj_cpf_socio
                            socio_str = socio
                        else:
                            # socio eh PF
                            socio = (cnpj_cpf_socio,nome_socio)
                            socio_str = cnpj_cpf_socio + nome_socio
                        
                        if cnpj == id_pessoa:
                        # eh socio da empresa em questao

                            # se o socio nao for a origem desse pulo
                            if socio != origem:
                                # chama recursivamente para tratar a nova PJ/PF
                                self._vinculos(tipo_pessoa=tipo_socio, id_pessoa=socio, nivel=nivel+1, origem=cnpj)

                                # adiciona aresta de socio para empresa em questao
                                self.G.add_edge(socio_str, 
                                                id_pessoa_str, 
                                                tipo='socio', 
                                                cod_qualificacao=cod_qualificacao, 
                                                data_entrada=data_entrada)

                        else:
                        # PJ ou PF em questao eh socia dessa empresa
                            # se a empresa nao for a origem desse pulo
                            if cnpj != origem:
                                self._vinculos(tipo_pessoa=1, id_pessoa=cnpj, nivel=nivel+1, origem=socio)

                                self.G.add_edge(socio_str, 
                                                cnpj, 
                                                tipo='socio', 
                                                cod_qualificacao=cod_qualificacao, 
                                                data_entrada=data_entrada)
                