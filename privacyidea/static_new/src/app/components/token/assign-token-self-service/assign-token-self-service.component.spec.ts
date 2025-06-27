import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AssignTokenSelfServiceComponent } from './assign-token-self-service.component';

describe('AssignTokenSelfServiceComponent', () => {
  let component: AssignTokenSelfServiceComponent;
  let fixture: ComponentFixture<AssignTokenSelfServiceComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AssignTokenSelfServiceComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AssignTokenSelfServiceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
