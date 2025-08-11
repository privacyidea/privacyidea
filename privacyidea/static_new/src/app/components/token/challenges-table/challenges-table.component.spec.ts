import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ChallengesTableComponent } from './challenges-table.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('ChallengesTableComponent', () => {
  let component: ChallengesTableComponent;
  let fixture: ComponentFixture<ChallengesTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChallengesTableComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(ChallengesTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
