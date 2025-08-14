import { ComponentFixture, TestBed } from "@angular/core/testing";

import { EnrollSmsComponent } from "./enroll-sms.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";

describe("EnrollSmsComponent", () => {
  let component: EnrollSmsComponent;
  let fixture: ComponentFixture<EnrollSmsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollSmsComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollSmsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
