import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainerRegistrationDialogComponent } from './container-registration-dialog.component';

describe('ContainerRegistrationDialogComponent', () => {
  let component: ContainerRegistrationDialogComponent;
  let fixture: ComponentFixture<ContainerRegistrationDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerRegistrationDialogComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ContainerRegistrationDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
