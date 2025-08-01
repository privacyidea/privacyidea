import { Component, signal } from '@angular/core';
import { TokenCardComponent } from './token-card.component';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  NoopAnimationsModule,
  provideNoopAnimations,
} from '@angular/platform-browser/animations';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { MatTabChangeEvent } from '@angular/material/tabs';
import { provideRouter } from '@angular/router';

@Component({ standalone: true, template: '' })
class DummyComponent {}

describe('TokenCardComponent', () => {
  let component: TokenCardComponent;
  let fixture: ComponentFixture<TokenCardComponent>;
  const mockEvent = (index: number): MatTabChangeEvent => ({
    index,
    tab: {} as any,
  });

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [TokenCardComponent, NoopAnimationsModule, DummyComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        provideRouter([
          {
            path: 'tokens',
            component: DummyComponent,
            children: [{ path: 'containers', component: DummyComponent }],
          },
        ]),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenCardComponent);
    component = fixture.componentInstance;
    component.selectedTabIndex = signal(0);
    component.tokenSerial = signal('Mock serial');
    component.containerSerial = signal('Mock container');
    component.states = signal([]);

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('onTabChange()', () => {
    it('should do nothing except reset `isProgrammaticChange` when it is true', () => {
      component.isProgrammaticTabChange.set(true);
      component.selectedTabIndex.set(1);
      component.containerSerial.set('Mock serial');
      component.tokenSerial.set('Mock serial');

      component.onTabChange(mockEvent(1));

      expect(component.selectedTabIndex()).toBe(1);
      expect(component.containerSerial()).toBe('Mock serial');
      expect(component.tokenSerial()).toBe('Mock serial');
    });
  });
});
