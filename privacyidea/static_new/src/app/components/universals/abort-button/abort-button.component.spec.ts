import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AbortButton } from './abort-button.component';

describe('AbortButton', () => {
  let component: AbortButton;
  let fixture: ComponentFixture<AbortButton>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AbortButton, BrowserAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(AbortButton);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
