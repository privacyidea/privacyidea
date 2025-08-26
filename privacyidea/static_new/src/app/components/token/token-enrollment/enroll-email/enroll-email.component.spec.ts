import { ComponentFixture, TestBed } from "@angular/core/testing";

import { EnrollEmailComponent } from "./enroll-email.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";

describe("EnrollEmailComponent", () => {
  let component: EnrollEmailComponent;
  let fixture: ComponentFixture<EnrollEmailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollEmailComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollEmailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
