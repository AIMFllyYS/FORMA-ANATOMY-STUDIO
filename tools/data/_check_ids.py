import json
ROOT = r'd:\projects\Dev-Web\Forma-Anatomy-Studio'
j = json.load(open(ROOT + r'\web\nomenclature.json', encoding='utf-8'))
recs = j['records']
ids = ['extensor_digitorum','extensor_digiti_minimi','extensor_indicis','pronator_quadratus',
 'flexor_pollicis_longus','flexor_digitorum_profundus','palmaris_longus_muscle',
 'humeral_head_of_flexor_carpi_ulnaris','ulnar_head_of_flexor_carpi_ulnaris',
 'humeral_head_of_extensor_carpi_ulnaris','ulnar_head_of_extensor_carpi_ulnaris',
 'radial_head_of_flexor_digitorum_superficialis','humero_ulnar_head_of_flexor_digitorum_superficialis',
 'radial_collateral_ligament_of_wrist_joint','ulnar_collateral_ligament_of_wrist_joint',
 'articular_disc_of_distal_radio_ulnar_joint','dorsal_radiocarpal_ligament','radiate_carpal_ligament',
 'palmar_carpometacarpal_ligaments','dorsal_intercarpal_ligaments']
for i in ids:
    r=recs.get(i)
    print('%-55s %s' % (i, (r.get('zh')+' / '+r.get('group','')+' / '+r.get('subgroup','')) if r else 'MISSING'))
