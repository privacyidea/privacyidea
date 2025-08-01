import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LayoutComponent } from './layout.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';

describe('LayoutComponent', () => {
  let component: LayoutComponent;
  let fixture: ComponentFixture<LayoutComponent>;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [LayoutComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        [
          {
            provide: ActivatedRoute,
            useValue: {
              params: of({ id: '123' }),
            },
          },
        ],
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(LayoutComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should render the header and router-outlet in the DOM', () => {
    fixture.detectChanges();

    const layoutElement = fixture.nativeElement.querySelector('.layout');
    expect(layoutElement).toBeTruthy();

    const header = fixture.nativeElement.querySelector(
      'header[aria-label="Header"]',
    );
    expect(header).toBeTruthy();

    const main = fixture.nativeElement.querySelector(
      'main[aria-label="Main Router Outlet"]',
    );
    expect(main).toBeTruthy();
  });
});
