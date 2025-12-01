import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PeriodicTaskPanelNewComponent } from './periodic-task-panel-new.component';

describe('PeriodicTaskPanelNewComponent', () => {
  let component: PeriodicTaskPanelNewComponent;
  let fixture: ComponentFixture<PeriodicTaskPanelNewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PeriodicTaskPanelNewComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PeriodicTaskPanelNewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
