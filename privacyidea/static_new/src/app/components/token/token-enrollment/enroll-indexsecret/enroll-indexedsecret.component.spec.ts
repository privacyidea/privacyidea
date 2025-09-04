import { ComponentFixture, TestBed } from "@angular/core/testing";
import "@angular/localize/init";
import { EnrollIndexedsecretComponent } from "./enroll-indexedsecret.component";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("EnrollIndexedsecretComponent", () => {
  let component: EnrollIndexedsecretComponent;
  let fixture: ComponentFixture<EnrollIndexedsecretComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollIndexedsecretComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollIndexedsecretComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
