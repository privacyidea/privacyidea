import { ComponentFixture, TestBed } from "@angular/core/testing";

import { EnrollFoureyesComponent } from "./enroll-foureyes.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";

describe("EnrollFoureyesComponent", () => {
  let component: EnrollFoureyesComponent;
  let fixture: ComponentFixture<EnrollFoureyesComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollFoureyesComponent, NoopAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollFoureyesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
