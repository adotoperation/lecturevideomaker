import json

with open(r'c:\Users\stone\Desktop\workspace\ai_lecture_maker\output_q32_processed.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

with open(r'c:\Users\stone\Desktop\workspace\ai_lecture_maker\preview_q32.txt', 'w', encoding='utf-8') as out:
    out.write('====================================================================\n')
    out.write('2026년 고3 6월 모의고사 32번: 대본 및 구조분석 데이터 검토\n')
    out.write('====================================================================\n\n')
    
    out.write('### [지문 요약 정보 (H열: 문장 1에 들어갈 데이터)]\n')
    out.write(json.dumps(d['analysis_data']['summary_info'], ensure_ascii=False, indent=2) + '\n\n')
    
    out.write('### [문장별 대본 (F열) 및 구문분석 (G열)]\n')
    for idx in range(1, 9):
        sent_data = d['analysis_data']['sentences'][idx - 1]
        script_text = d['scripts'].get(str(idx)) or d['scripts'].get(idx)
        out.write(f'--------------------------------------------------------------------\n')
        orig = sent_data.get('original', '')
        chunk = sent_data.get('chunk_korean', '')
        clause = sent_data.get('clause_structure', '')
        grammar = sent_data.get('grammar_points', '')
        tokens_len = len(sent_data.get('tokens', []))

        out.write(f'[문장 {idx}] 원문: {orig}\n')
        out.write(f'[문장 {idx}] 직독직해: {chunk}\n')
        out.write(f'[문장 {idx}] 형식분석: {clause}\n')
        out.write(f'[문장 {idx}] 문법포인트: {grammar}\n\n')
        out.write(f'[F열: 강의 대본]\n{script_text}\n\n')
        out.write(f'[G열: 구문분석 JSON 토큰 수]: {tokens_len} tokens\n\n')

print('Saved preview_q32.txt successfully!')
