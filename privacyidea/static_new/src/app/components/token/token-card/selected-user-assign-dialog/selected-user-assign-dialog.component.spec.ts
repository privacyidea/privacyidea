import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SelectedUserAssignDialogComponent } from './selected-user-assign-dialog.component';

describe('SelectedUserAssignDialogComponent', () => {
  let component: SelectedUserAssignDialogComponent;
  let fixture: ComponentFixture<SelectedUserAssignDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SelectedUserAssignDialogComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SelectedUserAssignDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
