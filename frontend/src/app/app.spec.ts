import { TestBed } from '@angular/core/testing';
import { App } from './app';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { IncidentService } from './services/incident.service';
import { DEFAULT_SYSTEM_CONFIG } from './core/config/system.config';

const DEMO_INCIDENT = {
  id: 'INC-5001',
  title: 'Elevated HTTP 500 errors on /api/v1/checkout post-deployment',
  service: 'checkout-service',
  severity: 'CRITICAL',
  status: 'INVESTIGATING',
  created_at: '2026-10-12T14:23:00.000Z',
  description:
    'Spike in 500 status codes immediately following release v2.4.1 deployment to production.',
  metrics_snapshot: {},
  logs: [],
};

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App, HttpClientTestingModule],
    }).compileComponents();

    // Ensure the backend API URL is deterministic in the test environment.
    const incidentService = TestBed.inject(IncidentService);
    incidentService.systemConfig.set({
      ...DEFAULT_SYSTEM_CONFIG,
      apiUrl: 'http://localhost:8000/api/v1',
    });
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should render the Zero500 brand', async () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges(); // triggers ngOnInit → health check + load incidents

    const httpMock = TestBed.inject(HttpTestingController);
    // Backend is unavailable in the test environment; respond with errors.
    httpMock.expectOne('http://localhost:8000/api/v1/health').error(new ErrorEvent('fail'));
    httpMock.expectOne('http://localhost:8000/api/v1/incidents').error(new ErrorEvent('fail'));

    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.brand-name')?.textContent).toContain('Zero500');
  });

  it('should render the selected incident title in the hero', async () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges(); // triggers ngOnInit → health check + load incidents

    const httpMock = TestBed.inject(HttpTestingController);
    // Backend unreachable → incidents fall back to the shared JSON fixture.
    httpMock.expectOne('http://localhost:8000/api/v1/health').error(new ErrorEvent('fail'));
    httpMock.expectOne('http://localhost:8000/api/v1/incidents').error(new ErrorEvent('fail'));
    httpMock.expectOne('assets/demo-incidents.json').flush([DEMO_INCIDENT]);
    // selectIncident(INC-5001) → getIncidentById → detail endpoint (mocked success).
    httpMock.expectOne('http://localhost:8000/api/v1/incidents/INC-5001').flush(DEMO_INCIDENT);

    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    const hero = compiled.querySelector('.hero-title') as HTMLElement | null;
    expect(hero?.textContent).toContain('Elevated HTTP 500 errors');
  });
});
