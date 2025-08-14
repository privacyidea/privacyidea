import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ClearableInputComponent } from './clearable-input.component';

describe('ClearableInputComponent', () => {
  let component: ClearableInputComponent;
  let fixture: ComponentFixture<ClearableInputComponent>;

  TestBed.configureTestingModule({
    imports: [ClearableInputComponent],
  }).compileComponents();

  beforeEach(() => {
    fixture = TestBed.createComponent(ClearableInputComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  it('should have showClearButton as true by default', () => {
    expect(component.showClearButton).toBe(true);
  });

  it('should emit onClick event when clearInput is called', () => {
    jest.spyOn(component.onClick, 'emit');
    component.clearInput();
    expect(component.onClick.emit).toHaveBeenCalled();
  });

  it('should allow showClearButton to be set to false', () => {
    component.showClearButton = false;
    expect(component.showClearButton).toBe(false);
  });
});
