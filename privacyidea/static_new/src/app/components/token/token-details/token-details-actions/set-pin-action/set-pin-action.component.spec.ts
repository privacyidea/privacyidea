import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SetPinActionComponent } from './set-pin-action.component';

describe('SetPinActionComponent', () => {
  let component: SetPinActionComponent;
  let fixture: ComponentFixture<SetPinActionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SetPinActionComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SetPinActionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
