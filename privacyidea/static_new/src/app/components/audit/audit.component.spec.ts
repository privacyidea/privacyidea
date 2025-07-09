import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AuditComponent } from './audit.component';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';

const activatedRouteStub = {
  snapshot: {
    paramMap: convertToParamMap({ id: '42' }),
    data: {},
  },

  paramMap: of(convertToParamMap({ id: '42' })),
  data: of({}),
};

describe('AuditComponent', () => {
  let component: AuditComponent;
  let fixture: ComponentFixture<AuditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        { provide: ActivatedRoute, useValue: activatedRouteStub },
        provideHttpClient(),
      ],
      imports: [AuditComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(AuditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
