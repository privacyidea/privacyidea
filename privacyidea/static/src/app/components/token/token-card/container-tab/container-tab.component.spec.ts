import {ComponentFixture, TestBed} from '@angular/core/testing';

import {ContainerTabComponent} from './container-tab.component';
import {provideHttpClient} from '@angular/common/http';
import {provideHttpClientTesting} from '@angular/common/http/testing';
import {signal} from '@angular/core';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

describe('ContainerTabComponent', () => {
  let component: ContainerTabComponent;
  let fixture: ComponentFixture<ContainerTabComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTabComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    })
      .compileComponents();

    fixture = TestBed.createComponent(ContainerTabComponent);
    component = fixture.componentInstance;
    component.containerIsSelected = signal(false);

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
