import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PeriodicTaskOptionDetailComponent } from './periodic-task-option-detail.component';

describe('PeriodicTaskOptionDetailComponent', () => {
  let component: PeriodicTaskOptionDetailComponent;
  let fixture: ComponentFixture<PeriodicTaskOptionDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PeriodicTaskOptionDetailComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PeriodicTaskOptionDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
