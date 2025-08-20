import { ComponentFixture, TestBed } from "@angular/core/testing";
import { NavigationSelfServiceComponent } from "./navigation-self-service.component";
import { provideHttpClient } from "@angular/common/http";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideAnimationsAsync } from "@angular/platform-browser/animations/async";
import { ActivatedRoute } from "@angular/router";
import { of } from "rxjs";

describe("NavigationSelfServiceComponent", () => {
  let component: NavigationSelfServiceComponent;
  let fixture: ComponentFixture<NavigationSelfServiceComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideAnimationsAsync(),
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        }
      ],
      imports: [NavigationSelfServiceComponent, BrowserAnimationsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(NavigationSelfServiceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
