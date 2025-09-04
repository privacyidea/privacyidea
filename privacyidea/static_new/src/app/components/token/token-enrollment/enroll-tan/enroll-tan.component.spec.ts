import { ComponentFixture, TestBed } from "@angular/core/testing";
import "@angular/localize/init";
import { EnrollTanComponent } from "./enroll-tan.component";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe("EnrollTanComponent", () => {
  let component: EnrollTanComponent;
  let fixture: ComponentFixture<EnrollTanComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollTanComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollTanComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
