import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NavigationSelfServiceButtonComponent } from './navigation-self-service-button.component';
import { provideHttpClient } from '@angular/common/http';

describe('NavigationSelfServiceButtonComponent', () => {
  let component: NavigationSelfServiceButtonComponent;
  let fixture: ComponentFixture<NavigationSelfServiceButtonComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [provideHttpClient()],
      imports: [NavigationSelfServiceButtonComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(NavigationSelfServiceButtonComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
