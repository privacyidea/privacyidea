import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { ConfirmButton } from './confirm-button.component';

describe('ConfirmButton', () => {
  let component: ConfirmButton;
  let fixture: ComponentFixture<ConfirmButton>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConfirmButton, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(ConfirmButton);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
