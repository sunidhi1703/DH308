"""Basic end-to-end smoke check against an isolated temporary database."""
import os
import tempfile
from unittest.mock import patch

with tempfile.TemporaryDirectory() as temp:
    os.environ['DATABASE_URL'] = f'sqlite:///{temp}/smoke.db'
    import seed
    from main import app
    from fastapi.testclient import TestClient
    from database import SessionLocal, engine
    from models import LabResult
    from routers.technician import _run_analyser
    client = TestClient(app)
    tokens = {}
    for username, password in [('recep1','recep123'),('nurse1','nurse123'),('doctor1','doc123'),('doctor2','doc456'),('coord1','coord123'),('tech1','tech123'),('tech2','tech456'),('patho1','patho123'),('patho2','patho456')]:
        r = client.post('/api/auth/token', data={'username':username,'password':password})
        assert r.status_code == 200, r.text
        tokens[username] = {'Authorization': f'Bearer {r.json()["access_token"]}'}
    def call(role, method, url, data=None, status=200):
        r = client.request(method, '/api/'+url, headers=tokens[role], json=data)
        assert r.status_code == status, (url,r.status_code,r.text)
        return r.json()
    p = call('recep1','POST','receptionist/patients',{'full_name':'Fictional Smoke Patient','dob':'1990-01-01','phone':'9000000000'})
    doctors = call('recep1','GET','receptionist/doctors')
    doctor = next(d for d in doctors if d['username']=='doctor1')
    v = call('recep1','POST','receptionist/visits',{'patient_id':p['id'],'doctor_id':doctor['id']})
    vid=v['id']
    call('recep1','POST',f'receptionist/visits/{vid}/reschedule',{'patient_id':p['id'],'doctor_id':doctor['id'],'appointment_time':'2026-10-15T12:00:00'})
    cancelled = call('recep1','POST','receptionist/visits',{'patient_id':p['id'],'doctor_id':doctor['id']})
    call('recep1','POST',f'receptionist/visits/{cancelled["id"]}/cancel')
    call('recep1','POST',f'receptionist/visits/{cancelled["id"]}/checkin',status=400)
    call('recep1','POST',f'receptionist/visits/{vid}/checkin')
    call('nurse1','POST',f'nurse/vitals/{vid}',{'pulse':80,'spo2':98,'chief_complaint':'Demo assessment'})
    chart = call('doctor1','GET',f'doctor/patients/{p["id"]}/current-visit')
    assert chart['id'] == vid and chart['vitals']['pulse'] == 80 and chart['vitals']['spo2'] == 98
    assert any(x['visit_id']==vid for x in call('doctor1','GET','doctor/dashboard')['my_patients'])
    assert not any(x['visit_id']==vid for x in call('doctor2','GET','doctor/dashboard')['my_patients'])
    assert not any(x['id']==vid for x in call('nurse1','GET','nurse/queue'))
    call('doctor1','POST',f'doctor/visits/{vid}/consultation',{'diagnosis':'Demo diagnosis'})
    saved_prescriptions = call('doctor1','POST',f'doctor/visits/{vid}/prescriptions',[{'medicine':'Demo medicine','dosage':'Demo only','frequency':'twice daily','duration':'5 days'}])
    assert saved_prescriptions[0]['frequency'] == 'twice daily'
    assert saved_prescriptions[0]['duration'] == '5 days'
    assert call('doctor1','GET',f'doctor/visits/{vid}/prescriptions') == saved_prescriptions
    for path in ['consultation','prescriptions']:
        call('doctor2','GET',f'doctor/visits/{vid}/{path}',status=403)
    call('doctor2','POST',f'doctor/visits/{vid}/prescriptions',[],403)
    tests=call('doctor1','GET','doctor/catalogue')
    tids=[t['id'] for t in tests if t['code'] in ('GLU','CBC')]
    call('doctor1','POST','doctor/lab-orders',{'visit_id':vid,'test_ids':[]},400)
    order=call('doctor1','POST','doctor/lab-orders',{'visit_id':vid,'test_ids':tids})
    tech=call('coord1','GET','coordinator/technicians')[0]
    reviewers=call('coord1','GET','coordinator/pathologists')
    assert all('hashed_password' not in x for x in reviewers)
    reviewer=next(x for x in reviewers if x['username']=='patho1')
    call('coord1','POST','coordinator/assign-technician',{'order_id':order['id'],'technician_id':tech['id']})
    collect={'order_id':order['id']}
    call('tech2','POST','technician/collect-sample',collect,403)
    call('tech1','POST','technician/collect-sample',collect)
    def sample(): return next(o for o in call('tech1','GET','technician/my-orders') if o['order_id']==order['id'])['sample']['id']
    old=sample()
    label = client.get(f'/api/technician/samples/{old}/label', headers=tokens['tech1'])
    assert label.status_code == 200 and '<svg' in label.text
    call('tech2','GET',f'technician/samples/{old}/label',status=403)
    call('tech1','POST',f'technician/receive-sample/{old}')
    call('tech1','POST','technician/reject-sample',{'sample_id':old,'rejection_reason':'Demo rejection'})
    call('tech1','POST','technician/collect-sample',collect)
    sid=sample(); assert sid!=old
    call('tech1','POST',f'technician/receive-sample/{sid}')
    with patch('time.sleep'):
        call('tech1','POST',f'technician/accept-sample/{sid}')
    results=call('tech1','GET',f'technician/results/{sid}')
    assert len(results)==2
    queues = call('patho1','GET','pathologist/review-queue') + call('patho2','GET','pathologist/review-queue')
    assert all(any(a['result_id'] == r['id'] for a in queues) for r in results)
    assert all(r['reviewer_username'] for r in results)
    call('tech2','GET',f'technician/results/{sid}',status=403)
    for r in results:
        call('coord1','POST','coordinator/assign-reviewer',{'result_id':r['id'],'pathologist_id':reviewer['id']})
    queue=call('patho1','GET','pathologist/review-queue')
    assignment=next(a for a in queue if a['result_id']==results[0]['id'])
    aid=assignment['assignment_id']
    call('tech1','POST',f'pathologist/review/{aid}',{'decision':'approved'},403)
    call('patho2','POST',f'pathologist/review/{aid}',{'decision':'approved'},403)
    call('patho1','POST',f'pathologist/review/{aid}',{'decision':'held','hold_reason':'Verify sample'})
    assert call('doctor1','GET',f'doctor/patients/{p["id"]}/reports')==[]
    call('patho1','POST',f'pathologist/review/{aid}',{'decision':'rerun','hold_reason':'Repeat for demo'})
    with patch('time.sleep'):
        call('tech1','POST',f'technician/request-rerun/{results[0]["id"]}')
    newer=call('tech1','GET',f'technician/results/{sid}')
    assert len(newer)==3 and newer[-1]['run_number']==2
    call('coord1','POST','coordinator/assign-reviewer',{'result_id':newer[-1]['id'],'pathologist_id':reviewer['id']})
    with SessionLocal() as db:
        db.query(LabResult).filter_by(id=newer[-1]['id']).first().flag='Glucose=HH'
        db.commit()
    queue=call('patho1','GET','pathologist/review-queue')
    for a in queue:
        if a['result_id'] not in [results[1]['id'],newer[-1]['id']]: continue
        if a['result_id']==newer[-1]['id']:
            call('patho1','POST',f'pathologist/review/{a["assignment_id"]}',{'decision':'approved'},400)
        call('patho1','POST',f'pathologist/review/{a["assignment_id"]}',{'decision':'approved','notification_recorded':True})
        call('patho1','POST',f'pathologist/review/{a["assignment_id"]}',{'decision':'approved','notification_recorded':True},400)
    call('doctor1','POST',f'doctor/visits/{vid}/complete')
    history = call('doctor1','GET',f'doctor/patients/{p["id"]}/visits')
    history_visit = next(visit for visit in history if visit['id'] == vid)
    history_prescription = history_visit['prescriptions'][0]
    assert history_prescription['frequency'] == 'twice daily'
    assert history_prescription['duration'] == '5 days'
    assert any(x['id']==p['id'] for x in call('doctor1','GET','doctor/patients'))
    assert any(x['id']==order['id'] for x in call('doctor1','GET',f'doctor/patients/{p["id"]}/lab-orders'))
    reports=call('doctor1','GET',f'doctor/patients/{p["id"]}/reports')
    assert len(reports)==2
    dash=call('doctor1','GET','doctor/dashboard')
    assert any(r['patient_id']==p['id'] for r in dash['report_items'])
    assert not any(o['id']==order['id'] for o in dash['pending_order_items'])
    for unknown in [999999,sid]:
        with patch('time.sleep'):
            try: _run_analyser(unknown,['GLU'])
            except ValueError: pass
            else: raise AssertionError('Invalid analyser message accepted')
    from datetime import date, timedelta
    follow_date = (date.today() + timedelta(days=7)).isoformat()
    follow_url = f'doctor/patients/{p["id"]}/follow-ups'
    payload = {'requested_date': follow_date, 'reason': 'Review recovery'}
    call('doctor2','POST',follow_url,payload,403)
    call('nurse1','GET','receptionist/follow-ups',status=403)
    call('doctor1','POST',follow_url,{'requested_date':'2000-01-01','reason':'Review'},400)
    follow = call('doctor1','POST',follow_url,payload)
    call('doctor1','POST',follow_url,payload,409)
    assert any(r['id']==follow['id'] for r in call('recep1','GET','receptionist/follow-ups'))
    book_url = f'receptionist/follow-ups/{follow["id"]}/book'
    booking = {'appointment_time':follow_date+'T10:00:00'}
    call('recep1','POST',book_url,{'appointment_time':'2000-01-01T10:00:00'},400)
    booked = call('recep1','POST',book_url,booking)
    assert booked['status'] == 'booked'
    call('recep1','POST',book_url,booking,409)
    assert call('doctor1','GET',follow_url)[0]['status']=='booked'
    assert any(v['patient_id']==p['id'] and v['appointment_time'].startswith(follow_date) for v in call('recep1','GET','receptionist/visits'))
    print('PASS: follow-up request, reception booking, duplicate prevention and access restrictions')
    print('PASS: all roles, registration through release, rejection/recollection, hold/rerun, critical notification, immutable reports and access denials')
    client.close()
    engine.dispose()
